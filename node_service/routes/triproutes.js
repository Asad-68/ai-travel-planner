const express = require("express");
const axios = require("axios");
const Trip = require("../models/Trip");
const authMiddleware = require("../middleware/authMiddleware");
const jwt = require("jsonwebtoken");

const router = express.Router();
const PYTHON_BASE_URL = process.env.PYTHON_SERVICE_URL || "http://localhost:5001";

function optionalAuth(req, res, next) {
  const authHeader = req.headers.authorization;
  if (authHeader && authHeader.startsWith("Bearer ")) {
    try {
      const decoded = jwt.verify(authHeader.split(" ")[1], process.env.JWT_SECRET);
      req.userId = decoded.userId;
    } catch { }
  }
  next();
}

router.post("/plan", optionalAuth, async (req, res) => {
  try {
    const body = req.body;

    const payload = {
      city: body.city,
      budget: body.budget,
      num_days: body.num_days,
      distance_km: body.distance_km,
      avg_hotel_per_night: body.avg_hotel_per_night,
      avg_food_per_day: body.avg_food_per_day,
      trip_type: body.trip_type,
      season: body.season,
      interest_nature: body.interest_nature,
      interest_heritage: body.interest_heritage,
      user_features: {
        avg_budget_per_day: body.avg_budget_per_day,
        preferred_trip_length: body.num_days,
        interest_nature: body.interest_nature,
        interest_heritage: body.interest_heritage,
        interest_nightlife: body.interest_nightlife,
      },
    };

    const pythonRes = await axios.post(`${PYTHON_BASE_URL}/api/plan-trip`, payload);

    const trip = await Trip.create({
      ...body,
      userId: req.userId || null,
      result: pythonRes.data,
    });

    res.json({ ...trip.result, _tripId: trip._id });
  } catch (err) {
    console.error(err.message);
    res.status(500).json({ error: "Failed to plan trip" });
  }
});

router.post("/save/:id", authMiddleware, async (req, res) => {
  try {
    const trip = await Trip.findById(req.params.id);
    if (!trip) return res.status(404).json({ error: "Trip not found" });
    if (trip.userId && trip.userId.toString() !== req.userId) {
      return res.status(403).json({ error: "Forbidden" });
    }
    trip.userId = req.userId;
    trip.saved = true;
    trip.title = req.body.title || `${trip.city} — ${trip.num_days} day${trip.num_days > 1 ? "s" : ""}`;
    await trip.save();
    res.json({ message: "Itinerary saved", trip });
  } catch (err) {
    console.error(err.message);
    res.status(500).json({ error: "Failed to save itinerary" });
  }
});

router.get("/saved", authMiddleware, async (req, res) => {
  try {
    const trips = await Trip.find({ userId: req.userId, saved: true }).sort({ createdAt: -1 });
    res.json(trips);
  } catch (err) {
    console.error(err.message);
    res.status(500).json({ error: "Failed to fetch saved trips" });
  }
});

router.delete("/saved/:id", authMiddleware, async (req, res) => {
  try {
    const trip = await Trip.findOneAndDelete({ _id: req.params.id, userId: req.userId });
    if (!trip) return res.status(404).json({ error: "Trip not found" });
    res.json({ message: "Trip deleted" });
  } catch (err) {
    console.error(err.message);
    res.status(500).json({ error: "Failed to delete trip" });
  }
});

router.get("/cities", async (req, res) => {
  try {
    const response = await axios.get(`${PYTHON_BASE_URL}/api/cities`);
    res.json(response.data);
  } catch (err) {
    console.error("Error fetching cities:", err.message);
    res.status(500).json({ error: "Failed to fetch cities" });
  }
});

router.post("/chat", async (req, res) => {
  try {
    const response = await axios.post(`${PYTHON_BASE_URL}/api/chat`, req.body);
    res.json(response.data);
  } catch (error) {
    console.error("Error in chat proxy:", error.message);
    res.status(500).json({ error: "Failed to chat with AI" });
  }
});

module.exports = router;
