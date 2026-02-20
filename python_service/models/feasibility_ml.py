import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import mean_absolute_error, accuracy_score

def load_trip_data(path="data/trips.csv"):
    return pd.read_csv(path)

def build_regression_model(df):
    X = df.drop(columns=["total_cost", "affordable"])
    y = df["total_cost"]

    numeric_features = [
        "budget", "num_days", "distance_km",
        "avg_hotel_per_night", "avg_food_per_day",
        "num_cities", "interest_nature", "interest_heritage"
    ]
    categorical_features = ["season", "trip_type"]

    numeric_transformer = StandardScaler()
    categorical_transformer = OneHotEncoder(handle_unknown="ignore")

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )

    reg = Pipeline(steps=[
        ("preprocess", preprocessor),
        ("model", LinearRegression()),
    ])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    reg.fit(X_train, y_train)
    return reg

def build_classification_model(df):
    X = df.drop(columns=["total_cost", "affordable"])
    y = df["affordable"]

    numeric_features = [
        "budget", "num_days", "distance_km",
        "avg_hotel_per_night", "avg_food_per_day",
        "num_cities", "interest_nature", "interest_heritage"
    ]
    categorical_features = ["season", "trip_type"]

    numeric_transformer = StandardScaler()
    categorical_transformer = OneHotEncoder(handle_unknown="ignore")

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )

    clf = Pipeline(steps=[
        ("preprocess", preprocessor),
        ("model", LogisticRegression(max_iter=1000)),
    ])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    clf.fit(X_train, y_train)
    return clf
