import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap
import os

print("Loading real data...")
df = pd.read_csv('data/100yr_complete.csv')
ann = pd.read_csv('data/100yr_annual.csv')

# Recent 10 years average rainfall per month
recent = df[df['year'] >= 2014]
monthly_avg = recent.groupby('month')['rainfall_mm'].mean()

# Compute dynamic risk score based on recent avg rainfall
max_rain = monthly_avg.max()
monsoon_avg = monthly_avg[[6,7,8,9]].mean()  # Jun-Sep

# Flood risk zones with coordinates
zones = [
    {'name': '🚨 Hindon River Bank',    'lat': 28.515,  'lon': 77.450,  'base_risk': 1.0, 'reason': 'River overflow zone'},
    {'name': '🚨 Bisrakh Village',       'lat': 28.520,  'lon': 77.470,  'base_risk': 1.0, 'reason': 'Hindon floodplain'},
    {'name': '🚨 Yamuna Expressway',     'lat': 28.430,  'lon': 77.480,  'base_risk': 1.0, 'reason': 'Flood corridor'},
    {'name': '🚨 Knowledge Park II',     'lat': 28.471,  'lon': 77.490,  'base_risk': 0.9, 'reason': 'Low-lying area'},
    {'name': '🚨 Kasna Village',         'lat': 28.450,  'lon': 77.500,  'base_risk': 0.9, 'reason': 'Near drainage channel'},
    {'name': '⚠️ Pari Chowk',           'lat': 28.4663, 'lon': 77.5034, 'base_risk': 0.6, 'reason': 'Junction flooding'},
    {'name': '⚠️ Surajpur Wetland',     'lat': 28.420,  'lon': 77.510,  'base_risk': 0.6, 'reason': 'Seasonal flooding'},
    {'name': '⚠️ Alpha 1 Sector',       'lat': 28.475,  'lon': 77.505,  'base_risk': 0.6, 'reason': 'Urban runoff'},
    {'name': '⚠️ Beta 2 Sector',        'lat': 28.480,  'lon': 77.515,  'base_risk': 0.6, 'reason': 'Low elevation'},
    {'name': '✅ Gamma Sector',          'lat': 28.485,  'lon': 77.520,  'base_risk': 0.2, 'reason': 'Adequate drainage'},
]

# Scale risk dynamically based on real monsoon rainfall
rain_scale = min(1.2, monsoon_avg / 150)  # normalize to expected ~150mm/month monsoon
for z in zones:
    z['risk'] = min(1.0, round(z['base_risk'] * rain_scale, 2))
    if z['risk'] >= 0.8:
        z['level'] = 'HIGH';   z['color'] = 'red';    z['radius'] = 500
    elif z['risk'] >= 0.5:
        z['level'] = 'MODERATE'; z['color'] = 'orange'; z['radius'] = 350
    else:
        z['level'] = 'LOW';    z['color'] = 'green';  z['radius'] = 250

# Build map
m = folium.Map(location=[28.4744, 77.504], zoom_start=12,
               tiles='https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
               attr='CartoDB')

# Stats box
avg_annual  = ann['rainfall_mm'].mean()
wettest     = ann.loc[ann['rainfall_mm'].idxmax()]
driest      = ann.loc[ann['rainfall_mm'].idxmin()]
recent_avg  = ann[ann['year']>=2014]['rainfall_mm'].mean()

stats_html = f"""
<div style="position:fixed;top:10px;right:10px;z-index:9999;background:white;
    padding:12px 16px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.3);
    font-family:Arial;font-size:13px;min-width:200px;">
  <b>📊 Greater Noida Rainfall</b><br>
  <hr style="margin:6px 0">
  Avg (100yr): <b>{avg_annual:.0f} mm/yr</b><br>
  Recent avg (2014-2024): <b>{recent_avg:.0f} mm/yr</b><br>
  Wettest: <b>{int(wettest.year)} ({wettest.rainfall_mm:.0f} mm)</b><br>
  Driest:  <b>{int(driest.year)} ({driest.rainfall_mm:.0f} mm)</b><br>
  Monsoon avg: <b>{monsoon_avg:.0f} mm/mo</b><br>
  <hr style="margin:6px 0">
  <span style="color:red">🔴 HIGH</span> &nbsp;
  <span style="color:orange">🟠 MOD</span> &nbsp;
  <span style="color:green">🟢 LOW</span>
</div>
"""
m.get_root().html.add_child(folium.Element(stats_html))

# Add zones
for z in zones:
    folium.Circle(
        location=[z['lat'], z['lon']],
        radius=z['radius'],
        color=z['color'], fill=True, fill_color=z['color'], fill_opacity=0.35, weight=2
    ).add_to(m)
    folium.Marker(
        location=[z['lat'], z['lon']],
        icon=folium.Icon(color=z['color'], icon='tint', prefix='fa'),
        popup=folium.Popup(
            f"<b>{z['name']}</b><br>Risk: {z['level']}<br>{z['reason']}<br>"
            f"<small>Score: {z['risk']:.2f} (monsoon: {monsoon_avg:.0f}mm/mo)</small>",
            max_width=220),
        tooltip=z['name']
    ).add_to(m)

# Heatmap
heat_data = [[z['lat'], z['lon'], z['risk']] for z in zones]
HeatMap(heat_data, min_opacity=0.5, radius=45, blur=30,
        gradient={'0.2':'green','0.5':'orange','1.0':'red'}).add_to(m)

os.makedirs('dashboard', exist_ok=True)
m.save('dashboard/flood_map.html')
print(f"✅ Map saved to dashboard/flood_map.html")
print(f"   Zones: {len(zones)} | Monsoon avg: {monsoon_avg:.1f} mm/mo | Risk scale: {rain_scale:.2f}")
