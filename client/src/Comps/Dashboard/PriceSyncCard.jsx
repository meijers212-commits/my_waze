// Comps/Dashboard/PriceSyncCard.jsx
// ─────────────────────────────────────────────────────────
// כרטיס המציג את מצב הסינכרון האחרון ומאפשר להפעיל ידנית.
// ─────────────────────────────────────────────────────────

import { useEffect, useState, useCallback } from "react";

const DATA_API_URL = import.meta.env.VITE_DATA_API_URL || "http://localhost:8000";

const POLL_INTERVAL_MS = 5000;

const PriceSyncCard = () => {
  const [status, setStatus]   = useState(null); // null | object
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const res  = await fetch(`${DATA_API_URL}/sync/status`);
      const data = await res.json();
      setStatus(data);
    } catch {
      /* silent — non-critical */
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll while sync is running
  useEffect(() => {
    fetchStatus();
    const id = setInterval(() => {
      if (status?.status === "running") fetchStatus();
    }, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchStatus, status?.status]);

  const handleTrigger = async () => {
    setTriggering(true);
    try {
      await fetch(`${DATA_API_URL}/sync/trigger`, { method: "POST" });
      // Give the server a moment to update state, then start polling
      setTimeout(fetchStatus, 1000);
    } finally {
      setTriggering(false);
    }
  };

  const isRunning = status?.status === "running" || triggering;

  const lastSyncLabel = () => {
    if (!status || status.status === "never_run") return "לא בוצע עדיין";
    if (status.status === "running") return "רץ כרגע...";
    if (status.finished_at) {
      return new Date(status.finished_at).toLocaleString("he-IL", {
        day: "numeric", month: "numeric", year: "2-digit",
        hour: "2-digit", minute: "2-digit",
      });
    }
    return "—";
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
      <div className="flex items-start justify-between gap-3">
        {/* אייקון + כותרת */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-violet-100 flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-violet-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </div>
          <div>
            <p className="font-semibold text-slate-800 text-sm">עדכון מחירים מרשתות</p>
            <p className="text-xs text-slate-400 mt-0.5">
              עדכון אחרון: <span className="text-slate-600">{loading ? "..." : lastSyncLabel()}</span>
            </p>
          </div>
        </div>

        {/* כפתור הפעלה */}
        <button
          onClick={handleTrigger}
          disabled={isRunning}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold
            bg-violet-600 hover:bg-violet-700 text-white disabled:opacity-50 disabled:cursor-not-allowed
            transition flex-shrink-0"
        >
          {isRunning ? (
            <>
              <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
              רץ...
            </>
          ) : (
            <>
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              עדכן עכשיו
            </>
          )}
        </button>
      </div>

      {/* תוצאות הסינכרון האחרון */}
      {status?.status === "completed" && (
        <div className="mt-4 grid grid-cols-3 gap-3">
          <div className="text-center">
            <p className="text-lg font-bold text-slate-900">{status.price_entries_added ?? 0}</p>
            <p className="text-xs text-slate-400">מחירים</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-slate-900">{status.products_created ?? 0}</p>
            <p className="text-xs text-slate-400">מוצרים חדשים</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-slate-900">{status.products_matched ?? 0}</p>
            <p className="text-xs text-slate-400">ממופים</p>
          </div>
        </div>
      )}

      {status?.status === "never_run" && (
        <p className="mt-3 text-xs text-amber-600 bg-amber-50 rounded-lg px-3 py-2">
          לחץ "עדכן עכשיו" כדי לשאוב מחירים עדכניים מכל הרשתות — זה עשוי לקחת מספר דקות.
        </p>
      )}
    </div>
  );
};

export default PriceSyncCard;
