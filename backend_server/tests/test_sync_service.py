import textwrap
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.services.sync_service import ScrapedPriceEntry, SyncResult, SyncService


# ── XML parsing ───────────────────────────────────────────────────────────────

SAMPLE_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="utf-8"?>
    <Root>
        <ChainName>שופרסל</ChainName>
        <Items>
            <Item>
                <ItemName>חלב תנובה 3%</ItemName>
                <ItemPrice>6.90</ItemPrice>
            </Item>
            <Item>
                <ItemName>לחם אחיד</ItemName>
                <ItemPrice>7.50</ItemPrice>
            </Item>
            <Item>
                <ItemName></ItemName>
                <ItemPrice>5.00</ItemPrice>
            </Item>
            <Item>
                <ItemName>מוצר ללא מחיר</ItemName>
                <ItemPrice>0</ItemPrice>
            </Item>
        </Items>
    </Root>
""").encode()


def test_parse_xml_bytes_returns_valid_items() -> None:
    service = SyncService()
    entries = list(service._parse_xml_bytes("test.xml", SAMPLE_XML))

    assert len(entries) == 2
    assert entries[0].store_name == "שופרסל"
    assert entries[0].product_name == "חלב תנובה 3%"
    assert entries[0].unit_price == 6.90
    assert isinstance(entries[0].price_date, date)


def test_parse_xml_bytes_skips_zero_price() -> None:
    service = SyncService()
    entries = list(service._parse_xml_bytes("test.xml", SAMPLE_XML))
    names = [e.product_name for e in entries]
    assert "מוצר ללא מחיר" not in names


def test_parse_xml_bytes_skips_empty_name() -> None:
    service = SyncService()
    entries = list(service._parse_xml_bytes("test.xml", SAMPLE_XML))
    assert all(e.product_name for e in entries)


def test_parse_invalid_xml_returns_empty() -> None:
    service = SyncService()
    entries = list(service._parse_xml_bytes("bad.xml", b"not xml at all"))
    assert entries == []


# ── SyncResult ────────────────────────────────────────────────────────────────

def test_sync_result_duration_none_before_finish() -> None:
    result = SyncResult()
    assert result.duration_seconds is None


def test_sync_result_to_dict_keys() -> None:
    from datetime import datetime

    result = SyncResult(
        products_created=5,
        products_matched=10,
        price_entries_added=15,
        errors=0,
        finished_at=datetime.utcnow(),
    )
    d = result.to_dict()
    assert "products_created" in d
    assert "price_entries_added" in d
    assert "duration_seconds" in d


# ── DB helpers (with mock session) ───────────────────────────────────────────

def _make_mock_session(existing_product=None, existing_store=None):
    session = MagicMock()
    session.scalar.side_effect = [existing_product, existing_store]
    return session


def test_get_or_create_product_creates_new() -> None:
    session = MagicMock()
    session.scalar.return_value = None  # nothing found

    result = SyncResult()
    product = SyncService._get_or_create_product(session, "חלב תנובה", "חלב תנובה", result)

    session.add.assert_called_once()
    session.flush.assert_called_once()
    assert result.products_created == 1
    assert result.products_matched == 0


def test_get_or_create_product_matches_existing() -> None:
    existing = MagicMock()
    existing.canonical_name = "חלב תנובה"

    session = MagicMock()
    session.scalar.return_value = existing

    result = SyncResult()
    product = SyncService._get_or_create_product(session, "חלב תנובה", "חלב תנובה", result)

    session.add.assert_not_called()
    assert result.products_matched == 1
    assert product is existing


def test_run_sync_returns_error_when_library_missing() -> None:
    service = SyncService()
    mock_session = MagicMock()

    with patch.dict("sys.modules", {"il_supermarket_scarper": None}):
        result = service.run_sync(mock_session)

    assert result.errors >= 1
    assert result.finished_at is not None
