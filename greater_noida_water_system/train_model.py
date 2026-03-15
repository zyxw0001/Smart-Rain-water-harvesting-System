import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from xgboost import XGBRegressor
import pickle, os

# ── Load data ───────────────────────────────────────────────────
df = pd.read_csv('data/100yr_complete.csv')
df = df.sort_values(['year','month']).reset_index(drop=True)
print(f"Data loaded: {df.shape} | Years: {df.year.min()}-{df.year.max()}")

# ── Simulate water level ────────────────────────────────────────
np.random.seed(42)
water = [0.0]
for i in range(1, len(df)):
    val = (0.85 * water[i-1] +
           0.60 * df.iloc[i]['rainfall_mm'] +
           0.10 * df.iloc[i]['soil_moisture'] +
           np.random.normal(0, 0.5))
    water.append(max(0, val))
df['water_level_cm'] = water

# ── Feature engineering ─────────────────────────────────────────
for i in range(1, 7):
    df[f'level_lag_{i}'] = df['water_level_cm'].shift(i)
    df[f'rain_lag_{i}']  = df['rainfall_mm'].shift(i)

# Rolling statistics
df['rain_roll3']  = df['rainfall_mm'].rolling(3).mean()
df['rain_roll6']  = df['rainfall_mm'].rolling(6).mean()
df['rain_roll12'] = df['rainfall_mm'].rolling(12).mean()
df['level_roll3'] = df['water_level_cm'].rolling(3).mean()

# Cyclical month encoding
df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
df['is_monsoon'] = df['month'].isin([6,7,8,9]).astype(int)
df['is_winter']  = df['month'].isin([11,12,1,2]).astype(int)

# Urban growth trend
df['urban_factor'] = 0.40 + (df['year'] - 1924) / 100 * 0.35

df.dropna(inplace=True)
print(f"After features: {df.shape}")

# ── Train/test split ────────────────────────────────────────────
drop_cols    = ['water_level_cm', 'source']
feature_cols = [c for c in df.columns if c not in drop_cols]
X = df[feature_cols]
y = df['water_level_cm']

split      = int(len(X) * 0.8)
X_train, X_test = X.iloc[:split], X.iloc[split:]
y_train, y_test = y.iloc[:split], y.iloc[split:]
print(f"Train: {len(X_train)} | Test: {len(X_test)}")

# ── Compare models ──────────────────────────────────────────────
models = {
    'Ridge':          Ridge(alpha=1.0),
    'RandomForest':   RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1),
    'GradientBoost':  GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, random_state=42),
    'XGBoost':        XGBRegressor(n_estimators=300, learning_rate=0.05, max_depth=6,
                                   subsample=0.8, colsample_bytree=0.8,
                                   random_state=42, verbosity=0),
}

print("\n=== Model Comparison ===")
best_model, best_r2, best_name = None, -999, ''
for name, mdl in models.items():
    mdl.fit(X_train, y_train)
    preds = mdl.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    r2  = r2_score(y_test, preds)
    print(f"  {name:20s} → MAE: {mae:7.3f} cm | R²: {r2:.4f}")
    if r2 > best_r2:
        best_r2, best_model, best_name = r2, mdl, name

print(f"\n🏆 Best: {best_name} (R²={best_r2:.4f})")

# ── Feature importance (XGBoost) ────────────────────────────────
xgb = models['XGBoost']
importances = pd.Series(xgb.feature_importances_, index=feature_cols)
print("\n Top 10 features (XGBoost):")
for feat, imp in importances.nlargest(10).items():
    bar = '█' * int(imp * 100)
    print(f"  {feat:25s} {imp:.4f}  {bar}")

# ── Save best model ─────────────────────────────────────────────
os.makedirs('models', exist_ok=True)
with open('models/water_model.pkl', 'wb') as f:
    pickle.dump({
        'model':        best_model,
        'features':     feature_cols,
        'best_name':    best_name,
        'best_r2':      best_r2,
        'xgb_model':    xgb,
        'feature_importance': importances.to_dict()
    }, f)

df.to_csv('data/greater_noida_processed.csv', index=False)
print("\nSaved: models/water_model.pkl")
print("Saved: data/greater_noida_processed.csv")

# ── Risk assessment ─────────────────────────────────────────────
recent = df[df['year'] >= 2020]
recent_max = recent['water_level_cm'].max()
print(f"\n=== Flood Risk (2020-2024) ===")
print(f"Max water level: {recent_max:.1f} cm")
if recent_max > 200:
    print("STATUS: 🚨 HIGH FLOOD RISK")
elif recent_max > 100:
    print("STATUS: ⚠️  MODERATE RISK")
else:
    print("STATUS: ✅ LOW RISK")
