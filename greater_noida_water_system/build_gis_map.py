import folium
from folium import plugins
from folium.plugins import HeatMap, MeasureControl, MiniMap
import pandas as pd
import numpy as np
import requests, json, os

print("Building Greater Noida GIS Map...")

LAT, LON = 28.4744, 77.5040

# ── Base map with multiple tile layers ─────────────────────────
m = folium.Map(location=[LAT, LON], zoom_start=12, control_scale=True)

# Tile layers
tiles = {
    'OpenStreetMap':  ('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                       '© OpenStreetMap contributors'),
    'Satellite':      ('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                       'Esri World Imagery'),
    'Dark Matter':    ('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
                       'CartoDB Dark Matter'),
    'Terrain':        ('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
                       'Esri World Topo'),
}
for name, (url, attr) in tiles.items():
    folium.TileLayer(url, name=name, attr=attr).add_to(m)

# ── Layer groups ────────────────────────────────────────────────
fg_boundary  = folium.FeatureGroup(name='🏙️ Greater Noida Boundary',  show=True)
fg_zones     = folium.FeatureGroup(name='🏘️ Planning Zones',           show=True)
fg_flood     = folium.FeatureGroup(name='🌊 Flood Risk Zones',          show=True)
fg_rivers    = folium.FeatureGroup(name='💧 Rivers & Water Bodies',     show=True)
fg_drain     = folium.FeatureGroup(name='🌿 Drainage Network',          show=False)
fg_recharge  = folium.FeatureGroup(name='♻️ Recharge Zones',            show=False)
fg_markers   = folium.FeatureGroup(name='📍 Monitoring Stations',       show=True)
fg_heatmap   = folium.FeatureGroup(name='🔥 Flood Risk Heatmap',        show=True)
fg_satellite = folium.FeatureGroup(name='📡 Weather Stations',          show=False)

# ── Greater Noida boundary (approximate polygon) ───────────────
boundary_coords = [
    [28.5700, 77.3900],[28.5800, 77.4200],[28.5750, 77.4600],
    [28.5600, 77.5000],[28.5400, 77.5300],[28.5100, 77.5500],
    [28.4800, 77.5600],[28.4500, 77.5500],[28.4200, 77.5300],
    [28.3900, 77.5100],[28.3800, 77.4800],[28.3900, 77.4400],
    [28.4100, 77.4000],[28.4400, 77.3700],[28.4800, 77.3600],
    [28.5200, 77.3700],[28.5500, 77.3800],[28.5700, 77.3900],
]
folium.Polygon(
    locations=boundary_coords,
    color='#00ff88', weight=3, fill=True,
    fill_color='#00ff88', fill_opacity=0.03,
    tooltip='Greater Noida Municipal Boundary'
).add_to(fg_boundary)

# ── Planning zones ──────────────────────────────────────────────
planning_zones = [
    ('Sector Alpha',    28.4750, 77.5050, 0.08, '#3498db', 'Residential Zone A'),
    ('Sector Beta',     28.4800, 77.5150, 0.08, '#3498db', 'Residential Zone B'),
    ('Sector Gamma',    28.4850, 77.5200, 0.08, '#2ecc71', 'Green Zone'),
    ('Knowledge Park',  28.4710, 77.4900, 0.10, '#9b59b6', 'Educational Zone'),
    ('Industrial Area', 28.5100, 77.5100, 0.10, '#e67e22', 'Industrial Zone'),
    ('Eco Zone',        28.4200, 77.5100, 0.12, '#27ae60', 'Eco/Wetland Zone'),
    ('Tech Zone',       28.4663, 77.5034, 0.08, '#1abc9c', 'IT/Commercial Zone'),
    ('Residential NW',  28.5050, 77.4300, 0.10, '#3498db', 'Residential Zone NW'),
]
for name, lat, lon, radius_deg, color, ztype in planning_zones:
    folium.Circle(
        location=[lat, lon],
        radius=radius_deg * 111000,
        color=color, fill=True, fill_opacity=0.12, weight=2,
        tooltip=f"<b>{name}</b><br>{ztype}"
    ).add_to(fg_zones)

# ── Rivers and water bodies ─────────────────────────────────────
# Hindon River (approximate path)
hindon = [[28.5800,77.4200],[28.5600,77.4350],[28.5400,77.4450],
          [28.5200,77.4500],[28.5000,77.4600],[28.4800,77.4700],
          [28.4600,77.4750],[28.4400,77.4700],[28.4200,77.4650]]
folium.PolyLine(hindon, color='#3498db', weight=4, opacity=0.8,
    tooltip='🌊 Hindon River').add_to(fg_rivers)
folium.PolyLine(hindon, color='#85c1e9', weight=8, opacity=0.2).add_to(fg_rivers)

# Yamuna River (western boundary)
yamuna = [[28.5700,77.3900],[28.5400,77.3800],[28.5100,77.3750],
          [28.4800,77.3600],[28.4500,77.3700],[28.4200,77.3900],
          [28.3900,77.4100]]
folium.PolyLine(yamuna, color='#2980b9', weight=5, opacity=0.8,
    tooltip='🌊 Yamuna River').add_to(fg_rivers)
folium.PolyLine(yamuna, color='#7fb3d3', weight=10, opacity=0.2).add_to(fg_rivers)

# Surajpur wetland
folium.Circle(location=[28.42, 77.51], radius=1200,
    color='#1abc9c', fill=True, fill_color='#1abc9c', fill_opacity=0.25,
    tooltip='💧 Surajpur Wetland').add_to(fg_rivers)

# Dhanauri wetland
folium.Circle(location=[28.38, 77.52], radius=800,
    color='#1abc9c', fill=True, fill_color='#1abc9c', fill_opacity=0.25,
    tooltip='💧 Dhanauri Wetland').add_to(fg_rivers)

# ── Drainage network ────────────────────────────────────────────
drainage_lines = [
    [[28.515,77.450],[28.490,77.470],[28.471,77.490],[28.450,77.500]],
    [[28.505,77.430],[28.490,77.450],[28.475,77.470],[28.460,77.480]],
    [[28.480,77.515],[28.470,77.505],[28.460,77.495],[28.450,77.490]],
    [[28.510,77.510],[28.500,77.505],[28.490,77.500],[28.480,77.495]],
]
for line in drainage_lines:
    folium.PolyLine(line, color='#27ae60', weight=2, opacity=0.7,
        dash_array='5', tooltip='Drainage Channel').add_to(fg_drain)

# ── Flood risk zones ────────────────────────────────────────────
flood_zones = [
    ('🚨 Hindon River Bank',  28.5150,77.4500,'HIGH',    'River overflow zone',    600),
    ('🚨 Bisrakh Village',    28.5200,77.4700,'HIGH',    'Hindon floodplain',      550),
    ('🚨 Yamuna Expressway',  28.4300,77.4800,'HIGH',    'Flood corridor',         600),
    ('🚨 Knowledge Park II',  28.4710,77.4900,'HIGH',    'Low-lying area',         500),
    ('🚨 Kasna Village',      28.4500,77.5000,'HIGH',    'Near drainage channel',  500),
    ('🚨 Greater Noida West', 28.5050,77.4300,'HIGH',    'Hindon proximity',       550),
    ('⚠️ Pari Chowk',         28.4663,77.5034,'MODERATE','Junction flooding',      400),
    ('⚠️ Surajpur Wetland',   28.4200,77.5100,'MODERATE','Seasonal flooding',      450),
    ('⚠️ Alpha 1 Sector',     28.4750,77.5050,'MODERATE','Urban runoff',           380),
    ('⚠️ Beta 2 Sector',      28.4800,77.5150,'MODERATE','Low elevation',          380),
    ('⚠️ Dadri Road',         28.5100,77.5100,'MODERATE','Road flooding',          400),
    ('✅ Gamma Sector',        28.4850,77.5200,'LOW',     'Adequate drainage',      250),
]
colors = {'HIGH':'#e74c3c','MODERATE':'#f39c12','LOW':'#2ecc71'}
for name,lat,lon,risk,reason,radius in flood_zones:
    folium.Circle(
        location=[lat,lon], radius=radius,
        color=colors[risk], fill=True,
        fill_color=colors[risk], fill_opacity=0.25, weight=2,
        popup=folium.Popup(
            f"""<div style='font-family:Arial;min-width:180px;padding:5px'>
            <b style='font-size:14px'>{name}</b><br>
            <hr style='margin:5px 0'>
            <b>Risk Level:</b> <span style='color:{colors[risk]}'>{risk}</span><br>
            <b>Reason:</b> {reason}<br>
            <b>Radius:</b> {radius}m impact zone
            </div>""", max_width=220),
        tooltip=f"{name} — {risk}"
    ).add_to(fg_flood)

# ── Recharge zones ──────────────────────────────────────────────
recharge_zones = [
    (28.4744, 77.5040, 800,  'Primary Recharge Zone',   'High percolation area'),
    (28.4900, 77.4800, 600,  'Secondary Recharge Zone', 'Moderate percolation'),
    (28.4600, 77.5200, 500,  'Tertiary Recharge Zone',  'Lower percolation'),
    (28.5000, 77.5000, 400,  'Urban Recharge Point',    'Rooftop harvesting zone'),
    (28.4400, 77.4900, 450,  'Agricultural Recharge',   'Farmland seepage zone'),
]
for lat,lon,radius,name,desc in recharge_zones:
    folium.Circle(
        location=[lat,lon], radius=radius,
        color='#00ff88', fill=True, fill_color='#00ff88', fill_opacity=0.2,
        weight=2, dash_array='8',
        tooltip=f"♻️ {name}: {desc}"
    ).add_to(fg_recharge)

# ── Monitoring stations ─────────────────────────────────────────
stations = [
    (28.4744, 77.5040, 'Main Station',       'water_level_cm', 462.5, '🟢'),
    (28.5150, 77.4500, 'Hindon Monitor',     'river_flow',     HIGH := 'HIGH', '🔴'),
    (28.4710, 77.4900, 'KP2 Station',        'groundwater',    12.3,  '🟡'),
    (28.4200, 77.5100, 'Surajpur Station',   'wetland_level',  45.2,  '🟢'),
    (28.4663, 77.5034, 'Pari Chowk Station', 'runoff',         23.1,  '🟡'),
    (28.5200, 77.4700, 'Bisrakh Station',    'flood_risk',     89.5,  '🔴'),
]
for lat,lon,name,metric,val,status in stations:
    folium.Marker(
        location=[lat,lon],
        icon=folium.DivIcon(html=f"""
            <div style='background:#1a1a2e;border:2px solid #00ff88;border-radius:50%;
                width:32px;height:32px;display:flex;align-items:center;justify-content:center;
                font-size:14px;box-shadow:0 0 8px #00ff8866'>{status}</div>""",
            icon_size=(32,32), icon_anchor=(16,16)),
        popup=folium.Popup(
            f"""<div style='font-family:Arial;min-width:160px;padding:5px'>
            <b>📡 {name}</b><br><hr style='margin:4px 0'>
            <b>Metric:</b> {metric}<br>
            <b>Reading:</b> {val}
            </div>""", max_width=200),
        tooltip=f"📡 {name}"
    ).add_to(fg_markers)

# ── Heatmap ─────────────────────────────────────────────────────
heat_data = [[lat,lon,1.0 if r=='HIGH' else 0.6 if r=='MODERATE' else 0.2]
             for _,lat,lon,r,_,_ in flood_zones]
HeatMap(heat_data, name='Flood Heatmap', radius=45, blur=30,
        gradient={'0.2':'green','0.5':'orange','1.0':'red'},
        min_opacity=0.4).add_to(fg_heatmap)

# ── Weather stations ────────────────────────────────────────────
weather_pts = [
    (28.4744, 77.5040, 'Central AWS', 33.5, 0.0,  45),
    (28.5150, 77.4500, 'North AWS',   32.8, 0.0,  48),
    (28.4200, 77.5100, 'South AWS',   34.1, 0.0,  42),
]
for lat,lon,name,temp,rain,humid in weather_pts:
    folium.Marker(
        location=[lat,lon],
        icon=folium.DivIcon(html=f"""
            <div style='background:#0d2137;border:1px solid #3498db;border-radius:4px;
                padding:3px 6px;font-size:10px;color:#3498db;white-space:nowrap'>
                🌡️{temp}°C 🌧️{rain}mm</div>""",
            icon_size=(90,24), icon_anchor=(45,12)),
        tooltip=f"📡 {name}: {temp}°C, Humidity {humid}%"
    ).add_to(fg_satellite)

# ── Add all layers ──────────────────────────────────────────────
for fg in [fg_boundary,fg_zones,fg_rivers,fg_drain,fg_flood,
           fg_recharge,fg_heatmap,fg_markers,fg_satellite]:
    fg.add_to(m)

# ── Controls ────────────────────────────────────────────────────
folium.LayerControl(collapsed=False, position='topright').add_to(m)
MeasureControl(position='bottomleft', primary_length_unit='meters').add_to(m)
MiniMap(toggle_display=True, position='bottomright').add_to(m)
plugins.Fullscreen(position='topleft').add_to(m)
plugins.LocateControl(position='topleft').add_to(m)

# ── Legend ──────────────────────────────────────────────────────
legend = """
<div style='position:fixed;bottom:30px;left:60px;z-index:9999;
    background:rgba(10,10,20,0.92);padding:14px 18px;border-radius:10px;
    border:1px solid #1a6b3c;font-family:Arial;font-size:12px;color:white;
    box-shadow:0 4px 15px rgba(0,0,0,0.5)'>
  <b style='font-size:13px'>📍 GIS Legend</b><br><hr style='margin:6px 0;border-color:#333'>
  <div>🔴 HIGH flood risk zone</div>
  <div>🟠 MODERATE flood risk</div>
  <div>🟢 LOW risk / Safe zone</div>
  <div>💧 Rivers & Wetlands</div>
  <div>♻️ Groundwater recharge</div>
  <div>�� Monitoring station</div>
  <div>🏙️ Municipal boundary</div>
  <hr style='margin:6px 0;border-color:#333'>
  <small style='color:#888'>Greater Noida • Lat:28.47 Lon:77.50</small>
</div>"""
m.get_root().html.add_child(folium.Element(legend))

os.makedirs('dashboard', exist_ok=True)
m.save('dashboard/gis_map.html')
print("✅ GIS map saved: dashboard/gis_map.html")
print(f"   Layers: Boundary, Zones, Rivers, Drainage, Flood Risk,")
print(f"           Recharge, Heatmap, Monitoring, Weather")
print(f"   Controls: Layer toggle, Measure tool, Minimap, Fullscreen")
