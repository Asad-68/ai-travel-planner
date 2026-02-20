const express = require("express");
const axios = require("axios");
const Trip = require("../models/Trip");

const router = express.Router();
const PYTHON_BASE_URL = process.env.PYTHON_SERVICE_URL || "http://localhost:5001";

router.post("/plan", async (req, res) => {
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
      result: pythonRes.data,
    });

    res.json(trip.result);
  } catch (err) {
    console.error(err.message);
    res.status(500).json({ error: "Failed to plan trip" });
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
