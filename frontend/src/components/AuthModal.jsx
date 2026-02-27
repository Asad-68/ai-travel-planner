import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import "./AuthModal.css";

export default function AuthModal({ onClose, onSuccess }) {
    const { login, register } = useAuth();
    const [mode, setMode] = useState("login");
    const [form, setForm] = useState({ name: "", email: "", password: "" });
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleChange = (e) => {
        setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
        setError("");
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError("");
        try {
            if (mode === "login") {
                await login(form.email, form.password);
            } else {
                await register(form.name, form.email, form.password);
            }
            onClose();
            if (onSuccess) onSuccess();
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-overlay" onClick={onClose}>
            <div className="auth-modal glass-card" onClick={(e) => e.stopPropagation()}>
                <button className="auth-close" onClick={onClose}>✕</button>

                <div className="auth-icon">🌍</div>
                <h2 className="auth-title">
                    {mode === "login" ? "Welcome Back" : "Join Wanderly"}
                </h2>
                <p className="auth-subtitle">
                    {mode === "login"
                        ? "Sign in to save and revisit your itineraries"
                        : "Create an account to start saving trips"}
                </p>

                <form className="auth-form" onSubmit={handleSubmit}>
                    {mode === "register" && (
                        <div className="auth-field">
                            <label>Full Name</label>
                            <input
                                type="text"
                                name="name"
                                placeholder="Your name"
                                value={form.name}
                                onChange={handleChange}
                                required
                                autoFocus
                            />
                        </div>
                    )}
                    <div className="auth-field">
                        <label>Email</label>
                        <input
                            type="email"
                            name="email"
                            placeholder="you@example.com"
                            value={form.email}
                            onChange={handleChange}
                            required
                            autoFocus={mode === "login"}
                        />
                    </div>
                    <div className="auth-field">
                        <label>Password</label>
                        <input
                            type="password"
                            name="password"
                            placeholder="••••••••"
                            value={form.password}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    {error && <div className="auth-error">⚠️ {error}</div>}

                    <button type="submit" className="btn-plan" disabled={loading}>
                        {loading ? (
                            <><span className="spinner"></span> {mode === "login" ? "Signing in…" : "Creating account…"}</>
                        ) : (
                            mode === "login" ? "Sign In" : "Create Account"
                        )}
                    </button>
                </form>

                <p className="auth-toggle">
                    {mode === "login" ? "New to Wanderly?" : "Already have an account?"}
                    <button
                        className="auth-toggle-btn"
                        onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}
                    >
                        {mode === "login" ? " Register" : " Sign in"}
                    </button>
                </p>
            </div>
        </div>
    );
}
