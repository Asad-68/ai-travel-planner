import React, { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { getSavedTrips, deleteTrip } from "../api/trips";
import "./SavedTrips.css";

export default function SavedTrips({ onLoad, onClose }) {
    const { user } = useAuth();
    const [trips, setTrips] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getSavedTrips()
            .then((data) => setTrips(Array.isArray(data) ? data : []))
            .finally(() => setLoading(false));
    }, []);

    const handleDelete = async (id) => {
        await deleteTrip(id);
        setTrips((prev) => prev.filter((t) => t._id !== id));
    };

    return (
        <div className="saved-overlay" onClick={onClose}>
            <div className="saved-panel glass-card" onClick={(e) => e.stopPropagation()}>
                <div className="saved-header">
                    <h2>📚 My Saved Trips</h2>
                    <button className="saved-close" onClick={onClose}>✕</button>
                </div>

                {loading ? (
                    <div className="saved-loading">
                        <span className="spinner"></span> Loading your trips…
                    </div>
                ) : trips.length === 0 ? (
                    <div className="saved-empty">
                        <div className="saved-empty-icon">🗺️</div>
                        <p>No saved itineraries yet.<br />Plan a trip and hit "Save Itinerary"!</p>
                    </div>
                ) : (
                    <ul className="saved-list">
                        {trips.map((trip) => (
                            <li key={trip._id} className="saved-card">
                                <div className="saved-card-info">
                                    <div className="saved-card-title">{trip.title || trip.city}</div>
                                    <div className="saved-card-meta">
                                        <span>📍 {trip.city}</span>
                                        <span>📅 {trip.num_days} day{trip.num_days > 1 ? "s" : ""}</span>
                                        <span>💸 ₹{trip.result?.predicted_total_cost?.toFixed(0)}</span>
                                    </div>
                                    <div className="saved-card-date">
                                        {new Date(trip.createdAt).toLocaleDateString("en-IN", {
                                            day: "numeric", month: "short", year: "numeric",
                                        })}
                                    </div>
                                </div>
                                <div className="saved-card-actions">
                                    <button
                                        className="btn-load"
                                        onClick={() => { onLoad(trip.result, trip._id); onClose(); }}
                                    >
                                        Load
                                    </button>
                                    <button
                                        className="btn-delete"
                                        onClick={() => handleDelete(trip._id)}
                                    >
                                        🗑️
                                    </button>
                                </div>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}
