import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Load the trained PatternAI state (as saved by pattern_ai.py)
with open("patternai_state.pkl", "rb") as f:
    state = pickle.load(f)

# Extract model and check initialization
model = state["model"]
initialized = state.get("initialized", False)

if not initialized:
    print("Modelul PatternAI nu este antrenat suficient pentru predicții.")
    exit()

# Prepare grid of days (0-6) and hours (0-23)
days = list(range(7))
hours = list(range(24))

# Generate predictions
pred_matrix = np.zeros((7, 24))
for d in days:
    for h in hours:
        X = np.array([[d, h]])
        pred_matrix[d, h] = model.predict(X)[0]

# Create DataFrame for display
df = pd.DataFrame(pred_matrix, index=[f"Ziua {d}" for d in days],
                  columns=[f"{h}:00" for h in hours])

print("Predicții PatternAI pe zile și ore")
print(df)

# Plot heatmap
plt.figure(figsize=(10, 6))
plt.imshow(pred_matrix, aspect='auto')
plt.colorbar(label="Nivel prezis (dB)")
plt.xticks(ticks=range(24), labels=hours)
plt.yticks(ticks=range(7), labels=[f"Ziua {d}" for d in days])
plt.xlabel("Oră (0-23)")
plt.ylabel("Ziua săptămânii (0=Luni)")
plt.title("Heatmap predicții PatternAI pentru fiecare oră și zi")
plt.tight_layout()
plt.show()
