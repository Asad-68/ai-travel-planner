import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS

from models.route_planners import load_pois, greedy_route
from models.feasibility_ml import load_trip_data, build_regression_model, build_classification_model
from models.personalization import load_user_data, build_kmeans_model, assign_cluster
from models.genai import generate_itinerary_narrative, chat_with_ai

app = Flask(__name__)
CORS(app)

trip_df = load_trip_data()
reg_model = build_regression_model(trip_df)
clf_model = build_classification_model(trip_df)

user_df = load_user_data()
scaler, kmeans = build_kmeans_model(user_df)

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message", "")
    itinerary = data.get("itinerary")
    response = chat_with_ai(message, itinerary)
    return jsonify({"reply": response})

@app.route("/api/plan-trip", methods=["POST"])
def plan_trip():
    data = request.json

    city = data.get("city", "Kolkata")
    budget = data["budget"]
    num_days = data["num_days"]
    distance_km = data["distance_km"]
    avg_hotel_per_night = data["avg_hotel_per_night"]
    avg_food_per_day = data["avg_food_per_day"]
    trip_type = data["trip_type"]
    season = data["season"]
    interest_nature = data["interest_nature"]
    interest_heritage = data["interest_heritage"]

    user_features = data["user_features"]
    cluster_id = assign_cluster(scaler, kmeans, user_features)

    pois = load_pois(city=city)

    remaining_pois = pois.copy()
    itinerary = {}
    total_time_spent = 0.0

    user_prefs = {
        "Nature": interest_nature,
        "Heritage": interest_heritage,
        "Nightlife": data.get("interest_nightlife", 0)
    }

    for day in range(1, num_days + 1):
        if remaining_pois.empty:
            break
        remaining_pois = remaining_pois.reset_index(drop=True)
        order, time_spent = greedy_route(remaining_pois, start_index=0, max_daily_hours=6)

        day_pois_data = remaining_pois.iloc[order][["name", "category", "avg_spend", "avg_stay_hours"]].to_dict(orient="records")

        narrative = generate_itinerary_narrative(city, day_pois_data, user_prefs)

        itinerary[f"day{day}"] = {
            "narrative": narrative,
            "pois": day_pois_data
        }

        total_time_spent += time_spent
        remaining_pois = remaining_pois.drop(remaining_pois.index[order]).reset_index(drop=True)

    X_input = pd.DataFrame([{
        "budget": budget,
        "num_days": num_days,
        "distance_km": distance_km,
        "avg_hotel_per_night": avg_hotel_per_night,
        "avg_food_per_day": avg_food_per_day,
        "num_cities": 1,
        "season": season,
        "trip_type": trip_type,
        "interest_nature": interest_nature,
        "interest_heritage": interest_heritage,
    }])

    predicted_cost = float(reg_model.predict(X_input)[0])
    affordable = predicted_cost <= budget

    return jsonify({
        "cluster_id": cluster_id,
        "itinerary": itinerary,
        "num_days": num_days,
        "time_spent_hours": total_time_spent,
        "predicted_total_cost": predicted_cost,
        "affordable": affordable,
    })

def get_unique_cities():
    df = pd.read_csv("data/pois.csv")
    return sorted(df["city"].unique().tolist())

@app.route("/api/cities", methods=["GET"])
def get_cities():
    cities = get_unique_cities()
    return jsonify(cities)

if __name__ == "__main__":
    app.run(port=5001, debug=True)
