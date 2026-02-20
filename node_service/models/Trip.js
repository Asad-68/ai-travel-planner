const mongoose = require("mongoose");

const TripSchema = new mongoose.Schema(
  {
    city: String,
    budget: Number,
    num_days: Number,
    distance_km: Number,
    avg_hotel_per_night: Number,
    avg_food_per_day: Number,
    trip_type: String,
    season: String,
    interest_nature: Number,
    interest_heritage: Number,
    avg_budget_per_day: Number,
    preferred_trip_length: Number,
    interest_nightlife: Number,
    result: Object,
  },
  { timestamps: true }
);

module.exports = mongoose.model("Trip", TripSchema);
