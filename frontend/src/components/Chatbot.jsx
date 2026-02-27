import React, { useState, useRef, useEffect } from "react";
import "./Chatbot.css";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:5000";

export default function Chatbot({ itinerary }) {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([
        { sender: "bot", text: "Hi! I'm Wanderly AI. How can I help with your trip?" },
    ]);
    const [loading, setLoading] = useState(false);
    const [showOptions, setShowOptions] = useState(true);
    const messagesEndRef = useRef(null);

    const toggleChat = () => setIsOpen(!isOpen);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    const handleAction = async (actionText) => {
        if (loading) return;

        const userMessage = { sender: "user", text: actionText };
        setMessages((prev) => [...prev, userMessage]);
        setLoading(true);
        setShowOptions(false);

        try {
            const res = await fetch(`${API_URL}/api/trips/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: actionText,
                    itinerary: itinerary
                }),
            });
            const data = await res.json();
            const botMessage = { sender: "bot", text: data.reply || "Sorry, I couldn't understand that." };
            setMessages((prev) => [...prev, botMessage]);
        } catch (error) {
            setMessages((prev) => [
                ...prev,
                { sender: "bot", text: "Oops! Something went wrong. Please try again." },
            ]);
        } finally {
            setLoading(false);
        }
    };

    const options = [
        "Packing tips",
        "Safety concerns",
        "What am I doing on Day 1?",
        "Tell me more about the spots I'm visiting today.",
        "What's the best thing on my itinerary?"
    ];

    return (
        <div className="chatbot-wrapper">
            {!isOpen && (
                <button className="chatbot-toggle" onClick={toggleChat}>
                    💬
                </button>
            )}

            {isOpen && (
                <div className="chatbot-window glass-card">
                    <div className="chatbot-header">
                        <span>Wanderly Assistant</span>
                        <button className="close-btn" onClick={toggleChat}>
                            ✕
                        </button>
                    </div>
                    <div className="chatbot-messages">
                        {messages.map((msg, idx) => (
                            <div key={idx} className={`message ${msg.sender}`} style={{ whiteSpace: "pre-wrap" }}>
                                {msg.text}
                            </div>
                        ))}
                        {loading && <div className="message bot">typing...</div>}
                        <div ref={messagesEndRef} />
                    </div>

                    {showOptions ? (
                        <div className="chatbot-options">
                            {options.map((option, index) => (
                                <button
                                    key={index}
                                    onClick={() => handleAction(option)}
                                    disabled={loading}
                                    className="option-btn"
                                >
                                    {option}
                                </button>
                            ))}
                            <button className="collapse-toggle" onClick={() => setShowOptions(false)}>
                                ✕ Close Menu
                            </button>
                        </div>
                    ) : (
                        <div className="chatbot-minimized-options">
                            <button className="expand-toggle" onClick={() => setShowOptions(true)}>
                                ➕ Ask another question
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
