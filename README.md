# Wanderly — AI Travel Planner

An AI-powered travel planning application that generates personalized multi-day itineraries with budget predictions, route optimization, and an interactive chatbot assistant.

## Architecture

```
├── frontend/          React app (port 3000)
├── node_service/      Express API gateway (port 5000)
└── python_service/    Flask ML & AI service (port 5001)
```

**Frontend** → React SPA with glassmorphism UI, dark/light theme toggle, trip planning form, itinerary display, and AI chatbot.

**Node Service** → Express server that proxies requests to the Python service and persists trip data in MongoDB.

**Python Service** → Flask server running ML models (cost regression, affordability classification, K-Means user clustering) and Gemini AI for narrative generation and chat.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vanilla CSS |
| API Gateway | Express 5, Mongoose |
| ML/AI Service | Flask, scikit-learn, Google Gemini |
| Database | MongoDB Atlas |

## Setup

### Prerequisites

- Node.js 18+
- Python 3.10+
- MongoDB Atlas account
- Google Gemini API key

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/ai-travel-planner.git
cd ai-travel-planner
```

```bash
cd node_service && npm install && cd ..
cd frontend && npm install && cd ..
cd python_service && pip install -r requirements.txt && cd ..
```

### 2. Configure Environment Variables

Copy the example files and fill in your credentials:

```bash
cp node_service/.env.example node_service/.env
cp python_service/.env.example python_service/.env
```

Edit `node_service/.env`:
```
MONGODB_URI=your_mongodb_connection_string
PYTHON_SERVICE_URL=http://localhost:5001
PORT=5000
```

Edit `python_service/.env`:
```
GEMINI_API_KEY=your_gemini_api_key
```

### 3. Run All Services

Open three terminals:

```bash
cd python_service && python app.py
```

```bash
cd node_service && npm start
```

```bash
cd frontend && npm start
```

The app will be available at **http://localhost:3000**.

## Features

- **AI Itinerary Generation** — Multi-day plans with Gemini-powered narratives
- **Budget Prediction** — ML regression model predicts total trip cost
- **Affordability Check** — Classification model flags over-budget trips
- **User Clustering** — K-Means personalization based on travel preferences
- **Route Optimization** — Greedy algorithm with haversine distance for daily POI ordering
- **AI Chatbot** — Context-aware travel assistant powered by Gemini
- **Dark/Light Theme** — Premium glassmorphism UI with theme toggle
