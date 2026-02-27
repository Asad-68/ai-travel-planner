import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import AuthModal from "./AuthModal";
import "./LandingPage.css";

const features = [
    {
        icon: "🗺️",
        title: "AI Itinerary Generator",
        description:
            "Get a fully personalised multi-day itinerary in seconds. Our AI plans every stop, every day — optimised for your interests.",
    },
    {
        icon: "💸",
        title: "Smart Budget Prediction",
        description:
            "ML regression models predict the real cost of your trip before you go, so there are no nasty surprises.",
    },
    {
        icon: "📍",
        title: "Route Optimisation",
        description:
            "A haversine-distance greedy algorithm arranges your daily stops for minimum travel time and maximum enjoyment.",
    },
    {
        icon: "🤖",
        title: "AI Travel Chatbot",
        description:
            "Ask Wanderly anything — packing tips, safety concerns, what to do on Day 2. Context-aware answers powered by Gemini.",
    },
    {
        icon: "💾",
        title: "Save Your Trips",
        description:
            "Sign in to save any generated itinerary and revisit it anytime. Your trips, your way, always available.",
    },
    {
        icon: "🎨",
        title: "Beautiful Dark & Light Mode",
        description:
            "A premium glassmorphism UI with smooth theme switching. Looks stunning day or night.",
    },
];

export default function LandingPage({ onEnterApp, theme, toggleTheme }) {
    const { user } = useAuth();
    const [showAuth, setShowAuth] = useState(false);

    const handleCTA = () => {
        if (user) {
            onEnterApp();
        } else {
            setShowAuth(true);
        }
    };

    return (
        <div className="landing-wrapper">
            <div className="landing-orb landing-orb-1" />
            <div className="landing-orb landing-orb-2" />
            <div className="landing-orb landing-orb-3" />

            <header className="landing-header">
                <div className="landing-logo">
                    <span className="landing-logo-icon">🌍</span>
                    <span className="landing-logo-text">Wanderly</span>
                </div>
                <nav className="landing-nav">
                    <a href="#features" className="landing-nav-link">Features</a>
                    <button className="landing-theme-toggle" onClick={toggleTheme} title="Switch Theme">
                        {theme === "dark" ? "☀️" : "🌙"}
                    </button>
                    {user ? (
                        <button className="btn-enter-app" onClick={onEnterApp}>
                            Open Planner →
                        </button>
                    ) : (
                        <button className="btn-enter-app" onClick={() => setShowAuth(true)}>
                            Sign In
                        </button>
                    )}
                </nav>
            </header>

            <section className="landing-hero">
                <div className="landing-hero-badge">
                    <span className="hero-badge-dot" />
                    AI-Powered Travel Planning
                </div>
                <h1 className="landing-hero-title">
                    Your next adventure,<br />
                    <span className="landing-gradient-text">planned by AI.</span>
                </h1>
                <p className="landing-hero-subtitle">
                    Wanderly crafts personalised multi-day itineraries with smart budget
                    prediction, route optimisation, and a context-aware travel chatbot — all in seconds.
                </p>

                <div className="landing-cta-group">
                    <button className="btn-cta-primary" onClick={handleCTA}>
                        {user ? "Open Planner →" : "Get Started"}
                    </button>
                    <a href="#features" className="btn-cta-secondary">
                        See Features ↓
                    </a>
                </div>

                <div className="landing-hero-scroll-hint">
                    <div className="scroll-mouse">
                        <div className="scroll-wheel" />
                    </div>
                </div>
            </section>

            <section className="landing-features" id="features">
                <div className="landing-section-label">What Wanderly Offers</div>
                <h2 className="landing-section-title">Everything you need to travel smarter</h2>
                <p className="landing-section-subtitle">
                    Six powerful features working together so you spend less time planning and more time exploring.
                </p>

                <div className="feature-grid">
                    {features.map((f, i) => (
                        <div
                            className="feature-card"
                            key={i}
                            style={{ animationDelay: `${i * 0.08}s` }}
                        >
                            <div className="feature-card-glow" />
                            <div className="feature-icon">{f.icon}</div>
                            <h3 className="feature-title">{f.title}</h3>
                            <p className="feature-desc">{f.description}</p>
                        </div>
                    ))}
                </div>
            </section>

            <section className="landing-cta-section">
                <div className="cta-card glass-bg">
                    <h2 className="cta-card-title">Ready to plan your next trip?</h2>
                    <p className="cta-card-sub">
                        Join Wanderly and start exploring smarter.
                    </p>
                    <button className="btn-cta-primary large" onClick={handleCTA}>
                        {user ? "Open Planner →" : "Start Planning"}
                    </button>
                </div>
            </section>

            <footer className="landing-footer">
                <p>&copy; 2026 Wanderly AI. Built for the modern traveler.</p>
            </footer>

            {showAuth && (
                <AuthModal
                    onClose={() => setShowAuth(false)}
                    onSuccess={onEnterApp}
                />
            )}
        </div>
    );
}
