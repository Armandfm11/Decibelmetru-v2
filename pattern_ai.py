# Librarii

# Ziua si ora colectarii esantionului
import datetime
import threading

# Array-uri
import numpy as np

# Serializare si deserializare
import pickle

# Path model antrenat
import os

from sklearn.ensemble import RandomForestRegressor



class PatternAI:
    def __init__(self, save_path=None):
        self._retrain_lock = threading.Lock()
        self._retrain_thread = None
        if save_path is None:
            save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patternai_state.pkl")
        self.save_path = save_path
        self.history = []
        self.model = RandomForestRegressor(n_estimators=100)
        self.initialized = False
        self._load_state()

    def add_observation(self, value: float):
        now = datetime.datetime.now()
        week_day = now.weekday()
        hour = now.hour + now.minute/60
        self.history.append((week_day, hour, value))
        # Start retraining in background if enough data and not already running
        if len(self.history) >= 50:
            if not self._retrain_thread or not self._retrain_thread.is_alive():
                self._retrain_thread = threading.Thread(target=self._retrain_model, daemon=True)
                self._retrain_thread.start()
        # Se salveaza progresul
        self._save_state()

    def _retrain_model(self):
        with self._retrain_lock:
            X = np.array([[d, h] for d, h, _ in self.history])
            y = np.array([v for _, _, v in self.history])
            self.model.fit(X, y)
            self.initialized = True
            # Save state after retraining
            self._save_state()

    def predict_current_pattern(self, ahead_minutes=0):
        if not self.initialized:
            return None
        now = datetime.datetime.now()
        week_day = now.weekday()
        hour = now.hour + now.minute/60 + ahead_minutes/60
        X_pred = np.array([[week_day, hour]])
        return float(self.model.predict(X_pred)[0])

    def _save_state(self):
        with open(self.save_path, "wb") as f:
            pickle.dump({
                "history": self.history,
                "model": self.model,
                "initialized": self.initialized
            }, f)

    def _load_state(self):
        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, "rb") as f:
                    state = pickle.load(f)
                    self.history = state.get("history", [])
                    self.model = state.get("model", RandomForestRegressor(n_estimators=100))
                    self.initialized = state.get("initialized", False)
                print(f"[PatternAI] State loaded from {self.save_path}")
            # Daca modelul nu poate fi incarcat/gasit, se incepe de la zero
            except Exception:
                self.history = []
                self.model = RandomForestRegressor(n_estimators=100)
                self.initialized = False
                print(f"[PatternAI] Failed to load state from {self.save_path}, starting fresh.")
