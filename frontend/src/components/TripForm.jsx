import React, { useState } from "react";
import { planTrip, fetchCities } from "../api/trips";

const defaultState = {
  city: "",
  budget: 5000,
  num_days: 2,
  distance_km: 300,
  avg_hotel_per_night: 800,
  avg_food_per_day: 300,
  trip_type: "solo",
  season: "winter",
  interest_nature: 1,
  interest_heritage: 1,
  avg_budget_per_day: 1500,
  interest_nightlife: 0,
};

export default function TripForm({ onPlan }) {
  const [form, setForm] = useState(defaultState);
  const [loading, setLoading] = useState(false);
  const [cities, setCities] = useState([]);

  React.useEffect(() => {
    fetchCities().then((data) => {
      setCities(data);
      if (data.length > 0) {
        setForm((prev) => ({ ...prev, city: data[0] }));
      }
    });
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    const numFields = [
      "budget",
      "num_days",
      "distance_km",
      "avg_hotel_per_night",
      "avg_food_per_day",
      "interest_nature",
      "interest_heritage",
      "avg_budget_per_day",
      "interest_nightlife",
    ];
    setForm((prev) => ({
      ...prev,
      [name]: numFields.includes(name) ? Number(value) : value,
    }));
  };

  const toggleInterest = (field) => {
    setForm((prev) => ({
      ...prev,
      [field]: prev[field] === 1 ? 0 : 1,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    await onPlan(form);
    setLoading(false);
  };

  return (
    <div className="glass-card fade-in">
      <div className="card-header">
        <div className="card-header-icon">🗺️</div>
        <h2>Plan Your Trip</h2>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-section-label">📍 Destination</div>
        <div className="form-row">
          <div className="form-group full-width">
            <label className="form-label">City</label>
            <select
              className="form-select"
              name="city"
              value={form.city}
              onChange={handleChange}
            >
              {cities.map((city) => (
                <option key={city} value={city}>
                  {city}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-section-label">💰 Budget & Duration</div>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Total Budget (₹)</label>
            <input
              className="form-input"
              name="budget"
              type="number"
              step="100"
              value={form.budget}
              onChange={handleChange}
              placeholder="5000"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Number of Days (1-5)</label>
            <input
              className="form-input"
              name="num_days"
              type="number"
              min="1"
              max="5"
              value={form.num_days}
              onChange={(e) => {
                let val = parseInt(e.target.value, 10);
                if (val > 5) val = 5;
                if (val < 1) val = 1;
                handleChange({ target: { name: "num_days", value: val } });
              }}
              placeholder="2"
            />
          </div>
        </div>

        <div className="form-section-label">⚙️ Preferences</div>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Trip Type</label>
            <select
              className="form-select"
              name="trip_type"
              value={form.trip_type}
              onChange={handleChange}
            >
              <option value="solo">🧍 Solo</option>
              <option value="couple">💑 Couple</option>
              <option value="family">👨‍👩‍👧‍👦 Family</option>
              <option value="friends">👯 Friends</option>
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Season</label>
            <select
              className="form-select"
              name="season"
              value={form.season}
              onChange={handleChange}
            >
              <option value="winter">❄️ Winter</option>
              <option value="summer">☀️ Summer</option>
              <option value="monsoon">🌧️ Monsoon</option>
              <option value="spring">🌸 Spring</option>
              <option value="autumn">🍂 Autumn</option>
            </select>
          </div>
        </div>

        <div className="form-section-label">🎯 Interests</div>
        <div className="toggle-group">
          <button
            type="button"
            className={`toggle-chip ${form.interest_nature ? "active" : ""}`}
            onClick={() => toggleInterest("interest_nature")}
          >
            🌿 Nature
          </button>
          <button
            type="button"
            className={`toggle-chip ${form.interest_heritage ? "active" : ""}`}
            onClick={() => toggleInterest("interest_heritage")}
          >
            🏛️ Heritage
          </button>
          <button
            type="button"
            className={`toggle-chip ${form.interest_nightlife ? "active" : ""}`}
            onClick={() => toggleInterest("interest_nightlife")}
          >
            🌃 Nightlife
          </button>
        </div>

        <button type="submit" className="btn-plan" disabled={loading}>
          {loading ? (
            <>
              <span className="spinner"></span>
              Generating Plan…
            </>
          ) : (
            "✨ Plan My Trip"
          )}
        </button>
      </form>
    </div>
  );
}
