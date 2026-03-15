import pandas as pd
import numpy as np
import pickle
import json
import requests
import folium
from folium.plugins import HeatMap
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from datetime import datetime
import os

# ── Load data & model ───────────────────────────────────────────
df = pd.read_csv('data/greater_noida_processed.csv')
df = df.sort_values(['year','month']).reset_index(drop=True)
df['date'] = pd.to_datetime(df[['year','month']].assign(day=1))

with open('models/water_model.pkl', 'rb') as f:
    saved = pickle.load(f)
model    = saved['model']
features = saved['features']
xgb      = saved.get('xgb_model', model)
fi       = saved.get('feature_importance', {})

# ── Fetch real-time weather ─────────────────────────────────────
def fetch_weather():
    try:
        r = requests.get('https://api.open-meteo.com/v1/forecast',
            params={'latitude':28.4744,'longitude':77.5040,
                    'current':'temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code',
                    'daily':'precipitation_sum,temperature_2m_max,temperature_2m_min',
                    'timezone':'Asia/Kolkata','forecast_days':7}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            with open('data/realtime_weather.json','w') as f:
                import json; json.dump(data, f)
            return data
    except: pass
    if os.path.exists('data/realtime_weather.json'):
        import json; return json.load(open('data/realtime_weather.json'))
    return None

# ── Generate map ────────────────────────────────────────────────
def generate_map():
    zones = [
        ('Hindon River Bank',  28.5150,77.4500,'HIGH',    'River overflow zone'),
        ('Bisrakh Village',    28.5200,77.4700,'HIGH',    'Hindon floodplain'),
        ('Yamuna Expressway',  28.4300,77.4800,'HIGH',    'Flood corridor'),
        ('Knowledge Park II',  28.4710,77.4900,'HIGH',    'Low-lying area'),
        ('Kasna Village',      28.4500,77.5000,'HIGH',    'Near drainage channel'),
        ('Greater Noida West', 28.5050,77.4300,'HIGH',    'Hindon river proximity'),
        ('Pari Chowk',         28.4663,77.5034,'MODERATE','Junction flooding'),
        ('Surajpur Wetland',   28.4200,77.5100,'MODERATE','Seasonal flooding'),
        ('Alpha 1 Sector',     28.4750,77.5050,'MODERATE','Urban runoff'),
        ('Beta 2 Sector',      28.4800,77.5150,'MODERATE','Low elevation'),
        ('Dadri Road',         28.5100,77.5100,'MODERATE','Road flooding history'),
        ('Gamma Sector',       28.4850,77.5200,'LOW',     'Adequate drainage'),
    ]
    colors = {'HIGH':'red','MODERATE':'orange','LOW':'green'}
    icons  = {'HIGH':'🚨','MODERATE':'⚠️','LOW':'✅'}
    m = folium.Map(location=[28.4744,77.5040], zoom_start=12, tiles='CartoDB dark_matter')
    for name,lat,lon,risk,reason in zones:
        folium.Circle(location=[lat,lon],
            radius=400 if risk=='HIGH' else 300 if risk=='MODERATE' else 200,
            color=colors[risk],fill=True,fill_opacity=0.3,weight=2).add_to(m)
        folium.Marker(location=[lat,lon],
            popup=folium.Popup(f"<div style='font-family:Arial;min-width:160px'><b>{icons[risk]} {name}</b><br><hr style='margin:4px 0'>Risk: <b style='color:{colors[risk]}'>{risk}</b><br>{reason}</div>",max_width=200),
            tooltip=f"{icons[risk]} {name}",
            icon=folium.Icon(color=colors[risk],icon='tint',prefix='fa')).add_to(m)
    heat = [[lat,lon,1.0 if r=='HIGH' else 0.6 if r=='MODERATE' else 0.2] for _,lat,lon,r,_ in zones]
    HeatMap(heat,radius=40,blur=25,gradient={'0.2':'green','0.6':'orange','1.0':'red'}).add_to(m)
    os.makedirs('dashboard',exist_ok=True)
    m.save('dashboard/flood_map.html')
    return open('dashboard/flood_map.html').read()

map_html = generate_map()

# ── App layout ──────────────────────────────────────────────────
app = Dash(__name__)
BG   = '#0a0a0f'
CARD = '#12121a'
BORDER = '#1e1e2e'

def card_style(border_color='#1a6b3c'):
    return {'background':CARD,'borderRadius':'12px','padding':'20px',
            'minWidth':'160px','textAlign':'center',
            'border':f'1px solid {border_color}',
            'boxShadow':f'0 0 15px {border_color}33'}

app.layout = html.Div(style={'backgroundColor':BG,'minHeight':'100vh','fontFamily':'"Segoe UI",Arial,sans-serif'}, children=[

    # ── Header ──
    html.Div(style={'background':'linear-gradient(135deg,#0d2137,#0d3b1e)','padding':'24px 30px',
                    'borderBottom':'1px solid #1a6b3c','display':'flex','justifyContent':'space-between','alignItems':'center'}, children=[
        html.Div([
            html.H1("💧 Greater Noida Smart Water System",
                style={'color':'white','margin':0,'fontSize':'24px','fontWeight':'700','letterSpacing':'0.5px'}),
            html.P("Real-Time Monitoring  •  AI Forecasting  •  Flood Alert System",
                style={'color':'#7fb3d3','margin':'4px 0 0 0','fontSize':'13px'})
        ]),
        html.Div([
            html.P(id='live-time', style={'color':'#82e0aa','fontSize':'12px','textAlign':'right','margin':0}),
            html.P("Auto-refresh: 30s", style={'color':'#555','fontSize':'11px','textAlign':'right','margin':0})
        ])
    ]),

    # ── Alert Banner ──
    html.Div(id='alert-banner'),

    # ── Real-time Weather Strip ──
    html.Div(id='weather-strip',
        style={'background':'#0d1117','borderBottom':'1px solid #1e1e2e','padding':'10px 30px',
               'display':'flex','gap':'30px','overflowX':'auto'}),

    # ── KPI Cards ──
    html.Div(style={'display':'flex','justifyContent':'center','gap':'16px','padding':'20px 30px','flexWrap':'wrap'}, children=[
        html.Div(id='card-water', style=card_style('#1a6b3c')),
        html.Div(id='card-rain',  style=card_style('#0d4a6e')),
        html.Div(id='card-temp',  style=card_style('#7d6608')),
        html.Div(id='card-humid', style=card_style('#4a0d6e')),
        html.Div(id='card-risk',  style=card_style('#922b21')),
    ]),

    # ── Charts Row 1 ──
    html.Div(style={'display':'grid','gridTemplateColumns':'1fr 1fr','gap':'16px','padding':'0 30px 16px'}, children=[
        dcc.Graph(id='water-chart'),
        dcc.Graph(id='rain-chart'),
    ]),

    # ── Forecast Chart ──
    html.Div(style={'padding':'0 30px 16px'}, children=[
        dcc.Graph(id='forecast-chart'),
    ]),

    # ── Feature Importance + Decade Chart ──
    html.Div(style={'display':'grid','gridTemplateColumns':'1fr 1fr','gap':'16px','padding':'0 30px 16px'}, children=[
        dcc.Graph(id='feature-chart'),
        dcc.Graph(id='decade-chart'),
    ]),

    # ── Map ──
    html.Div(style={'padding':'0 30px 30px'}, children=[
        html.Div(style={'background':CARD,'borderRadius':'12px','border':f'1px solid {BORDER}','overflow':'hidden'}, children=[
            html.Div(style={'padding':'16px 20px','borderBottom':f'1px solid {BORDER}','display':'flex','justifyContent':'space-between'}, children=[
                html.H3("🗺️ Greater Noida Flood Zone Map", style={'color':'white','margin':0,'fontSize':'16px'}),
                html.P("🔴 HIGH  🟠 MODERATE  🟢 LOW", style={'color':'#aaa','margin':0,'fontSize':'12px'})
            ]),
            html.Iframe(srcDoc=map_html,
                style={'width':'100%','height':'500px','border':'none','display':'block'})
        ])
    ]),

    # ── Footer ──
    html.Div(style={'textAlign':'center','padding':'16px','color':'#333','fontSize':'11px',
                    'borderTop':f'1px solid {BORDER}'}, children=[
        html.P("Greater Noida Smart Rainwater Harvesting & Flood Alert System  •  Data: NASA POWER + Open-Meteo  •  Model: XGBoost + Ridge")
    ]),

    dcc.Interval(id='interval', interval=30000, n_intervals=0)
])

# ── Callback ────────────────────────────────────────────────────
@app.callback(
    [Output('live-time','children'),
     Output('alert-banner','children'),
     Output('weather-strip','children'),
     Output('card-water','children'), Output('card-rain','children'),
     Output('card-temp','children'),  Output('card-humid','children'),
     Output('card-risk','children'),
     Output('water-chart','figure'),  Output('rain-chart','figure'),
     Output('forecast-chart','figure'),
     Output('feature-chart','figure'),Output('decade-chart','figure')],
    Input('interval','n_intervals')
)
def update(n):
    now    = datetime.now().strftime("%d %b %Y  %H:%M:%S")
    recent = df.tail(24)
    cur_water = float(df['water_level_cm'].iloc[-1])
    cur_rain  = float(df['rainfall_mm'].iloc[-1])
    weather_now = fetch_weather()
    live = weather_now.get('current', {}) if weather_now else {}
    cur_temp  = live.get('temperature_2m', float(df['temp_c'].iloc[-1]))
    cur_humid = live.get('relative_humidity_2m', float(df['humidity_pct'].iloc[-1]))
    cur_wind  = live.get('wind_speed_10m', 0.0)
    weather_icon = chr(9728) if live.get('weather_code',0)==0 else chr(127783)
    _ = None
    cur_humid = float(df['humidity_pct'].iloc[-1])

    # Risk level
    if cur_water > 200:
        risk,rc = 'HIGH','#e74c3c'
        alert = html.Div('🚨  FLOOD ALERT — Water level critical! Evacuate low-lying areas immediately!',
            style={'padding':'14px','textAlign':'center','fontSize':'16px','fontWeight':'bold',
                   'background':'linear-gradient(90deg,#7b0000,#922b21)','color':'white',
                   'borderBottom':'2px solid #e74c3c','letterSpacing':'1px'})
    elif cur_water > 100:
        risk,rc = 'MODERATE','#f39c12'
        alert = html.Div('⚠️  FLOOD WARNING — Water levels rising. Monitor situation closely.',
            style={'padding':'12px','textAlign':'center','fontSize':'15px','fontWeight':'bold',
                   'background':'#3d2b00','color':'#f39c12','borderBottom':'1px solid #f39c12'})
    else:
        risk,rc = 'LOW','#2ecc71'
        alert = html.Div('✅  All Clear — Normal water conditions across Greater Noida',
            style={'padding':'10px','textAlign':'center','fontSize':'13px',
                   'background':'#0d1f15','color':'#82e0aa','borderBottom':'1px solid #1a6b3c'})

    # Weather strip
    weather = fetch_weather()
    if weather:
        daily = weather['daily']
        weather_items = []
        for i in range(min(7, len(daily['time']))):
            date  = daily['time'][i][5:]  # MM-DD
            rain  = daily['precipitation_sum'][i] or 0
            tmax  = daily['temperature_2m_max'][i]
            tmin  = daily['temperature_2m_min'][i]
            rain_icon = '🌧️' if rain > 5 else '🌦️' if rain > 0 else '☀️'
            weather_items.append(html.Div([
                html.P(date, style={'color':'#888','fontSize':'11px','margin':'0'}),
                html.P(f"{rain_icon}", style={'fontSize':'18px','margin':'2px 0'}),
                html.P(f"{rain:.0f}mm", style={'color':'#3498db','fontSize':'11px','margin':'0'}),
                html.P(f"{tmax:.0f}°/{tmin:.0f}°", style={'color':'#f39c12','fontSize':'11px','margin':'0'}),
            ], style={'textAlign':'center','minWidth':'60px'}))
        weather_strip = [
            html.P("7-Day Forecast:", style={'color':'#555','fontSize':'11px','margin':'0 10px 0 0','alignSelf':'center'}),
            *weather_items
        ]
    else:
        weather_strip = [html.P("Weather data unavailable", style={'color':'#555','fontSize':'12px'})]

    # KPI card builder
    def kpi(icon, label, value, unit, color):
        return [
            html.P(f"{icon} {label}", style={'color':'#888','margin':'0','fontSize':'11px'}),
            html.H2(value, style={'color':color,'margin':'8px 0 4px','fontSize':'28px','fontWeight':'700'}),
            html.P(unit, style={'color':'#555','margin':'0','fontSize':'11px'})
        ]

    # 12-month forecast
    forecast_levels, cur = [], cur_water
    last = df.iloc[-1]
    for i in range(12):
        monthly_rain = max(0, float(last['rainfall_mm']) * 0.9 + np.random.normal(0,5))
        cur = max(0, 0.85*cur + 0.60*monthly_rain + 0.10*float(last['soil_moisture']))
        forecast_levels.append(cur)
    forecast_dates = pd.date_range(df['date'].iloc[-1], periods=13, freq='MS')[1:]

    layout_dark = dict(paper_bgcolor=CARD, plot_bgcolor=CARD, font_color='#ccc',
                       margin=dict(t=40,b=30,l=50,r=20),
                       xaxis=dict(gridcolor='#1e1e2e',color='#666'),
                       yaxis=dict(gridcolor='#1e1e2e',color='#666'),
                       legend=dict(bgcolor='rgba(0,0,0,0)'))

    # Water level chart
    w_fig = go.Figure()
    w_fig.add_trace(go.Scatter(x=recent['date'], y=recent['water_level_cm'],
        fill='tozeroy', fillcolor='rgba(46,204,113,0.1)',
        line=dict(color='#2ecc71',width=2), name='Water Level'))
    w_fig.add_hline(y=100, line_dash='dash', line_color='#f39c12', line_width=1)
    w_fig.add_hline(y=200, line_dash='dash', line_color='#e74c3c', line_width=1)
    w_fig.update_layout(**layout_dark, title='💧 Water Level — Last 24 Months (cm)', height=280)

    # Rainfall chart
    r_fig = go.Figure()
    r_fig.add_trace(go.Bar(x=recent['date'], y=recent['rainfall_mm'],
        marker_color=['#e74c3c' if v>150 else '#f39c12' if v>80 else '#3498db'
                      for v in recent['rainfall_mm']], name='Rainfall'))
    r_fig.update_layout(**layout_dark, title='🌧️ Rainfall — Last 24 Months (mm)', height=280)

    # Forecast chart
    f_fig = go.Figure()
    f_fig.add_trace(go.Scatter(x=recent['date'], y=recent['water_level_cm'],
        line=dict(color='#2ecc71',width=2), name='Historical'))
    f_fig.add_trace(go.Scatter(x=forecast_dates, y=forecast_levels,
        line=dict(color='#f39c12',dash='dot',width=2),
        fill='tozeroy', fillcolor='rgba(243,156,18,0.05)', name='12-Month Forecast'))
    f_fig.add_hline(y=100, line_dash='dash', line_color='#f39c12', line_width=1)
    f_fig.add_hline(y=200, line_dash='dash', line_color='#e74c3c', line_width=1)
    f_fig.update_layout(**layout_dark, title='📈 12-Month Water Level Forecast', height=300)

    # Feature importance chart
    if fi:
        top_fi = sorted(fi.items(), key=lambda x: x[1], reverse=True)[:8]
        fi_names = [x[0].replace('_',' ') for x in top_fi]
        fi_vals  = [x[1] for x in top_fi]
        feat_fig = go.Figure(go.Bar(
            x=fi_vals[::-1], y=fi_names[::-1], orientation='h',
            marker_color=['#2ecc71' if v > 0.1 else '#3498db' for v in fi_vals[::-1]]))
        feat_fig.update_layout(**layout_dark, title='🤖 XGBoost Feature Importance', height=300)
    else:
        feat_fig = go.Figure()
        feat_fig.update_layout(**layout_dark, title='Feature Importance', height=300)

    # Decade rainfall chart
    ann = df.groupby('year')['rainfall_mm'].sum().reset_index()
    ann['decade'] = (ann['year']//10)*10
    decade_avg = ann.groupby('decade')['rainfall_mm'].mean().reset_index()
    dec_fig = go.Figure(go.Bar(
        x=[f"{int(d)}s" for d in decade_avg['decade']],
        y=decade_avg['rainfall_mm'],
        marker_color=['#e74c3c' if v > 850 else '#f39c12' if v > 750 else '#3498db'
                      for v in decade_avg['rainfall_mm']],
        text=[f"{v:.0f}" for v in decade_avg['rainfall_mm']],
        textposition='outside', textfont=dict(color='#aaa', size=10)))
    dec_fig.update_layout(**layout_dark, title='📊 Decade Avg Rainfall (mm/yr)', height=300)

    return (
        f"Last updated: {now}",
        alert,
        weather_strip,
        kpi('💧','Water Level', f"{cur_water:.1f}", 'cm', '#2ecc71'),
        kpi('🌧️','Rainfall',    f"{cur_rain:.1f}",  'mm/mo', '#3498db'),
        kpi('🌡️','Temperature', f"{cur_temp:.1f}",  '°C', '#f39c12'),
        kpi('💨','Humidity',    f"{cur_humid:.1f}", '%', '#9b59b6'),
        kpi('⚠️','Flood Risk',   risk,              'status', rc),
        w_fig, r_fig, f_fig, feat_fig, dec_fig
    )

if __name__ == '__main__':
    print("🚀 Dashboard: http://127.0.0.1:8050")
    app.run(debug=False)
