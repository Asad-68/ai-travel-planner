import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { saveItinerary } from "../api/trips";

export default function ItineraryView({ result, tripId }) {
  const { user } = useAuth();
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState(false);

  const handleSave = async () => {
    if (!tripId) return;
    setSaving(true);
    await saveItinerary(tripId);
    setSaved(true);
    setSaving(false);
    setToast(true);
    setTimeout(() => setToast(false), 3000);
  };

  if (!result) {
    return (
      <div className="glass-card fade-in">
        <div className="itinerary-empty">
          <div className="itinerary-empty-icon">🧭</div>
          <h3>Your itinerary will appear here</h3>
          <p>Fill in your trip details and hit<br />"Plan My Trip" to get started.</p>
        </div>
      </div>
    );
  }

  const itinerary = result.itinerary || {};
  const dayKeys = Object.keys(itinerary).sort((a, b) => {
    const numA = parseInt(a.replace("day", ""), 10);
    const numB = parseInt(b.replace("day", ""), 10);
    return numA - numB;
  });

  return (
    <div className="glass-card fade-in" key={Date.now()}>
      {toast && <div className="save-toast">✅ Itinerary saved!</div>}

      <div className="card-header">
        <div className="card-header-icon">📋</div>
        <h2>Your AI Plan</h2>
        {user && tripId && (
          <button
            className={`btn-save-itinerary ${saved ? "saved" : ""}`}
            onClick={handleSave}
            disabled={saved || saving}
          >
            {saving ? <><span className="spinner"></span> Saving…</> : saved ? "✅ Saved" : "💾 Save"}
          </button>
        )}
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">💸</div>
          <div className="stat-value">₹{result.predicted_total_cost?.toFixed(0)}</div>
          <div className="stat-label">Predicted Cost</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">⏱️</div>
          <div className="stat-value">{result.time_spent_hours?.toFixed(1)}h</div>
          <div className="stat-label">Total Time</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">
            {result.affordable ? "✅" : "⚠️"}
          </div>
          <div className="stat-value">
            <span className={`badge ${result.affordable ? "badge-success" : "badge-warning"}`}>
              {result.affordable ? "Affordable" : "Over Budget"}
            </span>
          </div>
          <div className="stat-label">Budget Check</div>
        </div>
      </div>

      {dayKeys.map((dayKey) => {
        const dayNum = dayKey.replace("day", "");
        const dayData = itinerary[dayKey];
        const pois = Array.isArray(dayData) ? dayData : dayData.pois;
        const narrative = dayData.narrative;

        if (!pois || pois.length === 0) return null;

        return (
          <div key={dayKey} className="day-section fade-in-up">
            <div className="day-header">
              <span className="day-label">📅 Day {dayNum}</span>
              <span className="day-line"></span>
            </div>

            {narrative && (
              <div className="ai-narrative-card">
                <div className="ai-icon">✨ AI Insight</div>
                <p className="ai-text">{narrative}</p>
              </div>
            )}

            <ul className="poi-list">
              {pois.map((poi, idx) => (
                <li className="poi-card" key={idx}>
                  <div className="poi-number">{idx + 1}</div>
                  <div className="poi-info">
                    <div className="poi-name">{poi.name}</div>
                    <div className="poi-category">{poi.category}</div>
                  </div>
                  <div className="poi-meta">
                    <div className="poi-meta-item">
                      <div className="poi-meta-value">₹{poi.avg_spend}</div>
                      <div className="poi-meta-label">Cost</div>
                    </div>
                    <div className="poi-meta-item">
                      <div className="poi-meta-value">{poi.avg_stay_hours}h</div>
                      <div className="poi-meta-label">Duration</div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        );
      })}

      {dayKeys.length === 0 && (
        <p style={{ color: "var(--text-muted)", textAlign: "center", padding: "var(--space-lg) 0" }}>
          No itinerary data available for this city.
        </p>
      )}
    </div>
  );
}
