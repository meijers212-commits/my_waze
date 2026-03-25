from __future__ import annotations

import gzip
import logging
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.utils import normalize_product_name
from app.models.price_history import PriceHistory
from app.models.product import Product
from app.models.store import Store

logger = logging.getLogger(__name__)

# Major Israeli chains available in the il-supermarket-scraper library.
# Keep to chains known to the user; others can be added later via config.
DEFAULT_SCRAPERS: list[str] = [
    "SHUFERSAL",
    "RAMI_LEVY",
    "VICTORY",
    "YOHANANOF",
    "OSHER_AD",
    "HAZI_HINAM",
    "TIV_TAAM",
]

# One price file per chain per run is enough for weekly price snapshots.
DEFAULT_LIMIT_PER_CHAIN = 1


@dataclass
class ScrapedPriceEntry:
    store_name: str
    product_name: str
    unit_price: float
    price_date: date


@dataclass
class SyncResult:
    products_created: int = 0
    products_matched: int = 0
    price_entries_added: int = 0
    errors: int = 0
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None

    @property
    def duration_seconds(self) -> float | None:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    def to_dict(self) -> dict:
        return {
            "products_created": self.products_created,
            "products_matched": self.products_matched,
            "price_entries_added": self.price_entries_added,
            "errors": self.errors,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
        }


class SyncService:
    """
    Downloads and processes price data from Israeli supermarket chains via
    the il-supermarket-scraper library (backed by gov.il price transparency mandate).

    Typical weekly usage (called by the scheduler):
        service = SyncService()
        result = service.run_sync(db_session)

    Manual trigger for a subset of chains:
        result = service.run_sync(db_session, scrapers=["SHUFERSAL"], limit_per_chain=2)
    """

    def run_sync(
        self,
        db_session: Session,
        scrapers: list[str] | None = None,
        limit_per_chain: int = DEFAULT_LIMIT_PER_CHAIN,
    ) -> SyncResult:
        result = SyncResult()
        enabled = scrapers or DEFAULT_SCRAPERS
        logger.info(
            "Starting price sync. scrapers=%s limit_per_chain=%s", enabled, limit_per_chain
        )

        try:
            from il_supermarket_scarper import ScarpingTask  # noqa: PLC0415
            from il_supermarket_scarper.utils import FileTypesFilters  # noqa: PLC0415
        except ImportError:
            logger.error(
                "il-supermarket-scraper is not installed. "
                "Run: pip install il-supermarket-scraper"
            )
            result.errors += 1
            result.finished_at = datetime.utcnow()
            return result

        with tempfile.TemporaryDirectory() as dump_dir:
            logger.info("Downloading price files to temp dir: %s", dump_dir)
            try:
                task = ScarpingTask(
                    enabled_scrapers=enabled,
                    files_types=FileTypesFilters.only_price(),
                    # Single process — safer inside a web-server worker and on
                    # memory-constrained environments (e.g. Render free tier).
                    multiprocessing=1,
                    # Keep status files inside the temp dir so every run starts
                    # fresh. Without this the library writes to "dumps/status"
                    # (cwd-relative), marks today's files as "already downloaded",
                    # and every subsequent run in the same day returns 0 files.
                    output_configuration={
                        "output_mode": "disk",
                        "base_storage_path": dump_dir,
                    },
                    status_configuration={
                        "database_type": "json",
                        "base_path": f"{dump_dir}/status",
                    },
                )
                task.start(limit=limit_per_chain)
                task.join()
            except Exception:
                logger.exception("ScarpingTask failed during download phase")
                result.errors += 1
                result.finished_at = datetime.utcnow()
                return result

            # Count downloaded files for diagnostics.
            downloaded_files = list(Path(dump_dir).rglob("*.gz")) + list(
                Path(dump_dir).rglob("*.xml")
            )
            logger.info(
                "Download phase complete. Found %s price files. Parsing...",
                len(downloaded_files),
            )
            if not downloaded_files:
                logger.warning(
                    "No price files were downloaded. This may indicate that the "
                    "supermarket sites are geo-blocked or the scraper API changed."
                )

            for entry in self._iter_price_entries(Path(dump_dir)):
                try:
                    self._upsert_entry(db_session, entry, result)
                except Exception:
                    logger.exception("Failed to upsert entry: %s", entry)
                    result.errors += 1

        try:
            db_session.commit()
        except Exception:
            logger.exception("Commit failed after sync, rolling back")
            db_session.rollback()
            result.errors += 1

        result.finished_at = datetime.utcnow()
        logger.info(
            "Sync complete. created=%s matched=%s prices=%s errors=%s duration=%.1fs",
            result.products_created,
            result.products_matched,
            result.price_entries_added,
            result.errors,
            result.duration_seconds or 0,
        )
        return result

    # ── File iteration ────────────────────────────────────────────────────────

    def _iter_price_entries(self, dump_dir: Path) -> Iterator[ScrapedPriceEntry]:
        """Walk the dump directory and yield parsed price entries from all files."""
        for gz_file in dump_dir.rglob("*.gz"):
            yield from self._parse_gz_file(gz_file)
        for xml_file in dump_dir.rglob("*.xml"):
            yield from self._parse_xml_file(xml_file)

    def _parse_gz_file(self, gz_path: Path) -> Iterator[ScrapedPriceEntry]:
        try:
            with gzip.open(gz_path, "rb") as f:
                content = f.read()
            yield from self._parse_xml_bytes(gz_path.stem, content)
        except Exception:
            logger.warning("Skipping unreadable gz file: %s", gz_path.name)

    def _parse_xml_file(self, xml_path: Path) -> Iterator[ScrapedPriceEntry]:
        try:
            with open(xml_path, "rb") as f:
                content = f.read()
            yield from self._parse_xml_bytes(xml_path.name, content)
        except Exception:
            logger.warning("Skipping unreadable xml file: %s", xml_path.name)

    def _parse_xml_bytes(self, source_hint: str, content: bytes) -> Iterator[ScrapedPriceEntry]:
        """Parse raw XML bytes from a single chain price file."""
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            logger.warning("Invalid XML in file: %s", source_hint)
            return

        chain_name = (
            self._find_text(root, "ChainName")
            or self._find_text(root, "StoreName")
            or source_hint
        )

        # Israeli chains use either <Item>, <Price>, or <Product> as item elements.
        items = (
            root.findall(".//Item")
            or root.findall(".//Price")
            or root.findall(".//Product")
        )

        price_date = date.today()

        for item in items:
            name = self._find_text(item, "ItemName") or self._find_text(
                item, "ManufacturerItemDescription"
            ) or ""
            price_str = self._find_text(item, "ItemPrice") or self._find_text(
                item, "UnitOfMeasurePrice"
            ) or ""

            if not name or not price_str:
                continue

            try:
                price = float(price_str)
            except ValueError:
                continue

            if price <= 0:
                continue

            yield ScrapedPriceEntry(
                store_name=chain_name,
                product_name=name.strip(),
                unit_price=price,
                price_date=price_date,
            )

    # ── DB upsert helpers ─────────────────────────────────────────────────────

    def _upsert_entry(
        self, db_session: Session, entry: ScrapedPriceEntry, result: SyncResult
    ) -> None:
        canonical = normalize_product_name(entry.product_name)
        if not canonical:
            return

        store = self._get_or_create_store(db_session, entry.store_name)
        product = self._get_or_create_product(db_session, entry.product_name, canonical, result)

        price_row = PriceHistory(
            product_id=product.id,
            store_id=store.id,
            unit_price=round(entry.unit_price, 4),
            receipt_date=entry.price_date,
        )
        db_session.add(price_row)
        result.price_entries_added += 1

    @staticmethod
    def _get_or_create_store(db_session: Session, store_name: str) -> Store:
        normalized = " ".join(store_name.strip().split())
        existing = db_session.scalar(select(Store).where(Store.name == normalized))
        if existing:
            return existing
        store = Store(name=normalized)
        db_session.add(store)
        db_session.flush()
        return store

    @staticmethod
    def _get_or_create_product(
        db_session: Session,
        name: str,
        canonical: str,
        result: SyncResult,
    ) -> Product:
        # 1. Match by canonical_name (handles minor formatting differences).
        existing = db_session.scalar(
            select(Product).where(Product.canonical_name == canonical)
        )
        if existing:
            result.products_matched += 1
            return existing

        # 2. Fall back to exact name match (covers products from before migration
        #    that still have canonical_name=NULL).
        normalized_name = " ".join(name.strip().split())
        existing = db_session.scalar(
            select(Product).where(Product.name == normalized_name)
        )
        if existing:
            if existing.canonical_name is None:
                existing.canonical_name = canonical
                db_session.flush()
            result.products_matched += 1
            return existing

        # 3. Create new product from sync data.
        product = Product(name=normalized_name, canonical_name=canonical, source="sync")
        db_session.add(product)
        db_session.flush()
        result.products_created += 1
        return product

    @staticmethod
    def _find_text(element: ET.Element, tag: str) -> str | None:
        el = element.find(tag)
        return el.text.strip() if el is not None and el.text else None
