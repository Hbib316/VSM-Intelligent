import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import joblib, os

MODEL_PATH = "models/wait_model.joblib"
CLASSIFIER_PATH = "models/critical_model.joblib"

class MLAnalyzer:
    """Modèle scikit-learn pour estimer les temps d'attente anormaux ou goulots."""

    def __init__(self):
        self.pipeline = None
        self.classifier = None
        os.makedirs("models", exist_ok=True)
        
        # Load or train regression model
        if os.path.exists(MODEL_PATH):
            try:
                self.pipeline = joblib.load(MODEL_PATH)
            except Exception:
                self.pipeline = None
        if self.pipeline is None:
            self.train()
        
        # Load or train classification model
        if os.path.exists(CLASSIFIER_PATH):
            try:
                self.classifier = joblib.load(CLASSIFIER_PATH)
            except Exception:
                self.classifier = None
        if self.classifier is None:
            self.train_classifier()

    def train(self):
        """Dataset synthétique d'apprentissage pour régression"""
        data = []
        for cycle in [1, 2, 3, 5, 8]:
            for cost in [200, 600, 1000, 1800]:
                for va in [0, 1]:
                    wait = (0.2 * cycle) + (0.002 * cost) + (2 if va == 0 else 0.5)
                    data.append({
                        "cycle_time": cycle,
                        "cost": cost,
                        "value_added": va,
                        "wait_time": wait
                    })
        df = pd.DataFrame(data)
        X = df[["cycle_time", "cost", "value_added"]]
        y = df["wait_time"]
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("rf", RandomForestRegressor(n_estimators=100, random_state=42))
        ])
        self.pipeline.fit(X, y)
        joblib.dump(self.pipeline, MODEL_PATH)

    def train_classifier(self):
        """Dataset synthétique pour classification des étapes critiques"""
        data = []
        for cycle in [1, 2, 3, 5, 8, 10, 15]:
            for cost in [200, 600, 1000, 1800, 3000]:
                for va in [0, 1]:
                    wait = (0.2 * cycle) + (0.002 * cost) + (2 if va == 0 else 0.5)
                    # Étape critique si: cycle > 5h OU (wait/cycle > 0.5 ET !VA)
                    is_critical = 1 if (cycle > 5 or (wait/max(cycle, 0.1) > 0.5 and va == 0)) else 0
                    data.append({
                        "cycle_time": cycle,
                        "cost": cost,
                        "value_added": va,
                        "wait_time": wait,
                        "is_critical": is_critical
                    })
        df = pd.DataFrame(data)
        X = df[["cycle_time", "cost", "value_added", "wait_time"]]
        y = df["is_critical"]
        self.classifier = Pipeline([
            ("scaler", StandardScaler()),
            ("rf", RandomForestClassifier(n_estimators=100, random_state=42))
        ])
        self.classifier.fit(X, y)
        joblib.dump(self.classifier, CLASSIFIER_PATH)

    def predict_wait_time(self, step):
        """Prédire le temps d'attente pour une étape"""
        if not self.pipeline:
            self.train()
        X = pd.DataFrame([{
            "cycle_time": step.get("cycle_time", 0),
            "cost": step.get("cost", 0),
            "value_added": 1 if step.get("value_added") else 0
        }])
        pred = float(self.pipeline.predict(X)[0])
        return round(pred, 2)

    def predict_critical_flags(self, steps):
        """Prédire si les étapes sont critiques (goulots d'étranglement)"""
        if not self.classifier:
            self.train_classifier()
        
        if not steps:
            return []
        
        # Préparer les features pour chaque étape
        features = []
        for s in steps:
            features.append({
                "cycle_time": s.get("cycle_time", 0),
                "cost": s.get("cost", 0),
                "value_added": 1 if s.get("value_added") else 0,
                "wait_time": s.get("wait_time", 0)
            })
        
        X = pd.DataFrame(features)
        predictions = self.classifier.predict(X)
        return predictions.tolist()