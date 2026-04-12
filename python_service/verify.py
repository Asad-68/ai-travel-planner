"""
verify.py — End-to-end verification of the production AI Travel Planner backend.
Run with: .\venv\Scripts\python.exe verify.py
"""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)

print("=" * 60)
print("STEP 1: ModelRegistry — load from disk (no retraining)")
print("=" * 60)
from services.model_registry import ModelRegistry
reg = ModelRegistry()
reg.load_or_train()
print("reg_model :", type(reg.reg_model).__name__)
print("clf_model :", type(reg.clf_model).__name__)
print("kmeans k  :", reg.kmeans.n_clusters)
print("features  :", reg.feature_cols[:4], "...")
print("PASS")

print()
print("=" * 60)
print("STEP 2: Force retrain + save to disk")
print("=" * 60)
reg2 = ModelRegistry()
reg2.load_or_train(force_retrain=True)
print("reg_model :", type(reg2.reg_model).__name__)
print("kmeans k  :", reg2.kmeans.n_clusters)
print("PASS")

print()
print("=" * 60)
print("STEP 3: Cluster assignment + persona label")
print("=" * 60)
feat = {
    "avg_budget_per_day": 1200,
    "preferred_trip_length": 3,
    "interest_nature": 1,
    "interest_heritage": 0,
}
cid   = reg2.assign_cluster(feat)
label = reg2.cluster_label(cid)
print(f"cluster_id : {cid}")
print(f"label      : {label}")
print("PASS")

print()
print("=" * 60)
print("STEP 4: Input validation")
print("=" * 60)
from services.trip_service import validate_trip_input

bad_errors = validate_trip_input({"city": "Delhi", "budget": -500})
print("Errors on bad input (expected > 0):", len(bad_errors), "errors")
assert len(bad_errors) > 0, "Should have caught missing/bad fields"

good_payload = {
    "city": "Delhi", "budget": 8000, "num_days": 2,
    "distance_km": 300, "avg_hotel_per_night": 900,
    "avg_food_per_day": 400, "trip_type": "friends",
    "season": "winter", "interest_nature": 1, "interest_heritage": 1,
}
good_errors = validate_trip_input(good_payload)
print("Errors on valid input (expected 0):", good_errors)
assert good_errors == [], f"Unexpected errors: {good_errors}"
print("PASS")

print()
print("=" * 60)
print("STEP 5: plan_trip service (no Gemini — fallback narrative)")
print("=" * 60)
from services.trip_service import plan_trip

result = plan_trip({**good_payload, "user_features": {}}, registry=reg2)
print("status          :", result["status"])
print("days planned    :", len(result["itinerary"]))
print("cluster_label   :", result["cluster_label"])
print("total_cost      :", result["predicted_total_cost"])
print("affordable      :", result["affordable"])
print("cost_breakdown  :", result["cost_breakdown"])
assert result["status"] == "ok"
assert len(result["itinerary"]) == good_payload["num_days"]
assert "hotel" in result["cost_breakdown"]
print("PASS")

print()
print("=" * 60)
print("STEP 6: Multi-day route (3 days, Kolkata)")
print("=" * 60)
result3 = plan_trip({
    "city": "Kolkata", "budget": 12000, "num_days": 3,
    "distance_km": 200, "avg_hotel_per_night": 1000,
    "avg_food_per_day": 500, "trip_type": "family",
    "season": "winter", "interest_nature": 1, "interest_heritage": 1,
    "user_features": {},
}, registry=reg2)
print(f"Days planned: {len(result3['itinerary'])}")
for day_key, day_data in result3["itinerary"].items():
    poi_names = [p["name"] for p in day_data["pois"]]
    print(f"  {day_key}: {len(poi_names)} POIs — {poi_names}")
assert len(result3["itinerary"]) == 3
print("PASS")

print()
print("=" * 60)
print("STEP 7: ConversationMemory")
print("=" * 60)
from models.genai import ConversationMemory
mem = ConversationMemory(max_turns=3)
mem.add("What is the best time to visit Goa?", "October to March is the best time.")
mem.add("Suggest beach activities.", "Try surfing, parasailing, and sunset cruises.")
print(f"Memory length : {len(mem)}")
formatted = mem.format_for_prompt()
print("Memory preview:", formatted[:80].replace("\n", " | "))
assert len(mem) == 2
print("PASS")

print()
print("=" * 60)
print("STEP 8: Invalid city gracefully handled")
print("=" * 60)
result_empty = plan_trip({
    "city": "NonExistentCity99", "budget": 5000, "num_days": 1,
    "distance_km": 100, "avg_hotel_per_night": 500,
    "avg_food_per_day": 200, "trip_type": "solo",
    "season": "summer", "interest_nature": 1, "interest_heritage": 0,
    "user_features": {},
}, registry=reg2)
print("status  :", result_empty["status"])
print("itinerary empty:", result_empty["itinerary"] == {})
assert result_empty["status"] == "ok"
assert result_empty["itinerary"] == {}
print("PASS")

print()
print("=" * 60)
print("ALL VERIFICATION STEPS PASSED")
print("=" * 60)
