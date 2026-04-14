import React, { useState, useEffect } from "react";
import TripForm from "./components/TripForm";
import ItineraryView from "./components/ItineraryView";
import { planTrip } from "./api/trips";
import Chatbot from "./components/Chatbot";
import AuthModal from "./components/AuthModal";
import SavedTrips from "./components/SavedTrips";
import LandingPage from "./components/LandingPage";
import { AuthProvider, useAuth } from "./context/AuthContext";
import "./styles/App.css";

function AppInner() {
  const { user, logout } = useAuth();
  const [view, setView] = useState("landing");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [tripId, setTripId] = useState(null);
  const [planError, setPlanError] = useState(null);
  const [theme, setTheme] = useState("dark");
  const [showAuth, setShowAuth] = useState(false);
  const [showSaved, setShowSaved] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  useEffect(() => {
    document.body.className = `${theme}-theme`;
  }, [theme]);

  const toggleTheme = () => setTheme(prev => (prev === "dark" ? "light" : "dark"));

  const handleLogout = () => {
    logout();
    setView("landing");
  };

  const handlePlan = async (formData) => {
    setLoading(true);
    setResult(null);     // clear stale result on each new attempt
    setPlanError(null);
    try {
      const data = await planTrip(formData);
      if (data && data.error) {
        setPlanError(data.error);
      } else {
        setTripId(data._tripId || null);
        setResult(data);
      }
    } catch (err) {
      setPlanError(err.message || "Failed to connect to the server. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleLoadSaved = (savedResult) => {
    setResult(savedResult);
    setTripId(null);
  };

  if (view === "landing") {
    return (
      <LandingPage
        onEnterApp={() => setView("app")}
        theme={theme}
        toggleTheme={toggleTheme}
      />
    );
  }

  return (
    <div className="app-wrapper">
      <header className="app-header">
        <button className="app-logo" onClick={() => setView("landing")} style={{ background: "none", border: "none", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.5rem", padding: 0 }}>
          <span className="app-logo-icon">🌍</span>
          <span className="app-logo-text">Wanderly</span>
        </button>
        <div className="app-header-right">
          <button className="theme-toggle-btn" onClick={toggleTheme} title="Switch Theme">
            {theme === "dark" ? "☀️" : "🌙"}
          </button>

          {user ? (
            <div className="user-menu-wrapper">
              <button
                className="user-avatar-btn"
                onClick={() => setUserMenuOpen(prev => !prev)}
              >
                <span className="user-avatar-initials">
                  {user.name.charAt(0).toUpperCase()}
                </span>
                <span className="user-name-label">{user.name.split(" ")[0]}</span>
                <span className="user-menu-caret">▾</span>
              </button>
              {userMenuOpen && (
                <div className="user-dropdown glass-card" onClick={() => setUserMenuOpen(false)}>
                  <button className="user-dropdown-item" onClick={() => setShowSaved(true)}>
                    📚 My Trips
                  </button>
                  <div className="user-dropdown-divider"></div>
                  <button className="user-dropdown-item danger" onClick={handleLogout}>
                    🚪 Sign Out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <button className="btn-login-header" onClick={() => setShowAuth(true)}>
              Sign In
            </button>
          )}

          <div className="app-header-badge">
            <span className="dot"></span>
            AI Powered
          </div>
        </div>
      </header>

      <section className="hero-section">
        <div className="hero-tagline">Your personal AI travel planner</div>
        <h1 className="hero-title">
          Travel Smarter with <span className="gradient-text">AI Precision</span>
        </h1>
        <p className="hero-subtitle">
          From budget-friendly escapes to luxury adventures, our AI crafts the perfect itinerary just for you.
        </p>
      </section>

      <main className="main-content">
        <div className="content-grid">
          <TripForm onPlan={handlePlan} loading={loading} />
          <ItineraryView result={result} tripId={tripId} error={planError} />
        </div>
        <Chatbot itinerary={result} />
      </main>

      <footer className="app-footer">
        <p>&copy; 2026 Wanderly AI. Built for the modern traveler.</p>
      </footer>

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} onSuccess={() => setView("app")} />}
      {showSaved && (
        <SavedTrips
          onLoad={handleLoadSaved}
          onClose={() => setShowSaved(false)}
        />
      )}
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  );
}
