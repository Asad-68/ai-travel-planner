import math
import pandas as pd

def load_pois(path="data/pois.csv", city="Kolkata"):
    df = pd.read_csv(path)
    return df[df["city"] == city].reset_index(drop=True)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def build_distance_matrix(pois):
    n = len(pois)
    dist = [[0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            dist[i][j] = haversine(
                pois.loc[i, "lat"], pois.loc[i, "lon"],
                pois.loc[j, "lat"], pois.loc[j, "lon"],
            )
    return dist

def greedy_route(pois, start_index=0, max_daily_hours=8):
    dist = build_distance_matrix(pois)
    n = len(pois)
    visited = [False]*n
    order = [start_index]
    visited[start_index] = True
    time_spent = float(pois.loc[start_index, "avg_stay_hours"])

    while True:
        current = order[-1]
        best_score = -1
        best_idx = None

        for j in range(n):
            if visited[j] or j == current:
                continue
            d = dist[current][j]
            score = float(pois.loc[j, "rating"]) / (1 + d)
            stay = float(pois.loc[j, "avg_stay_hours"])
            if time_spent + stay > max_daily_hours:
                continue
            if score > best_score:
                best_score = score
                best_idx = j

        if best_idx is None:
            break

        order.append(best_idx)
        visited[best_idx] = True
        time_spent += float(pois.loc[best_idx, "avg_stay_hours"])

    return order, time_spent
