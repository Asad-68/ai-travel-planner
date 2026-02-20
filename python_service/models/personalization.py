import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import numpy as np

def load_user_data(path="data/users.csv"):
    return pd.read_csv(path)

def build_kmeans_model(df, k=3):
    feature_cols = [
        "avg_budget_per_day",
        "preferred_trip_length",
        "interest_nature",
        "interest_heritage",
        "interest_nightlife",
    ]
    X = df[feature_cols]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=k, random_state=42)
    kmeans.fit(X_scaled)

    df["cluster"] = kmeans.predict(X_scaled)
    return scaler, kmeans

def assign_cluster(scaler, kmeans, user_features):
    cols = [
        "avg_budget_per_day",
        "preferred_trip_length",
        "interest_nature",
        "interest_heritage",
        "interest_nightlife",
    ]
    x = np.array([[user_features[c] for c in cols]])
    x_scaled = scaler.transform(x)
    cluster = kmeans.predict(x_scaled)[0]
    return int(cluster)
