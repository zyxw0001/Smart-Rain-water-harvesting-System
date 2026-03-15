import pandas as pd
import numpy as np
import pickle
import folium
from folium.plugins import HeatMap
from dash import Dash, dcc, html, Input, Output, State
import plotly.graph_objs as go
from datetime import datetime
import os

df = pd.read_csv('data/greater_noida_processed.csv', parse_dates=['time'], index_col='time')
with open('models/water_model.pkl', 'rb') as f:
    model = pickle.load(f)

def generate_map():
    flood_zones = [
        ('Hindon River Bank',  28.5150,77.4500,'HIGH',    'River overflow zone'),
        ('Knowledge Park II',  28.4710,77.4900,'HIGH',    'Low-lying area'),
        ('Kasna Village',      28.4500,77.5000,'HIGH',    'Near drainage channel'),
        ('Surajpur Wetland',   28.4200,77.5100,'MODERATE','Seasonal flooding'),
        ('Alpha 1 Sector',     28.4750,77.5050,'MODERATE','Urban runoff'),
        ('Beta 2 Sector',      28.4800,77.5150,'MODERATE','Low elevation'),
        ('Gamma Sector',       28.4850,77.5200,'LOW',     'Adequate drainage'),
        ('Pari Chowk',         28.4663,77.5034,'MODERATE','Junction flooding'),
        ('Yamuna Expressway',  28.4300,77.4800,'HIGH',    'Flood corridor'),
        ('Bisrakh Village',    28.5200,77.4700,'HIGH',    'Hindon floodplain'),
    ]
    colors = {'HIGH':'red','MODERATE':'orange','LOW':'green'}
    icons  = {'HIGH':'🚨','MODERATE':'⚠️','LOW':'✅'}
    m = folium.Map(location=[28.4744,77.5040], zoom_start=12,
                   tiles='https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
                   attr='CartoDB')
    for name,lat,lon,risk,reason in flood_zones:
        folium.Circle(location=[lat,lon],
            radius=500 if risk=='HIGH' else 350 if risk=='MODERATE' else 250,
            color=colors[risk], fill=True, fill_opacity=0.35, weight=2).add_to(m)
        folium.Marker(location=[lat,lon],
            popup=folium.Popup(f'<b>{icons[risk]} {name}</b><br>Risk: {risk}<br>{reason}', max_width=200),
            tooltip=f"{icons[risk]} {name}",
            icon=folium.Icon(color=colors[risk], icon='tint', prefix='fa')).add_to(m)
    heat = [[lat,lon,1.0 if r=='HIGH' else 0.6 if r=='MODERATE' else 0.2]
            for _,lat,lon,r,_ in flood_zones]
    HeatMap(heat, radius=45, blur=30,
            gradient={'0.2':'green','0.5':'orange','1.0':'red'}).add_to(m)
    os.makedirs('dashboard', exist_ok=True)
    m.save('dashboard/flood_map.html')
    return open('dashboard/flood_map.html').read()

map_html = generate_map()

# ── Styles ────────────────────────────────────────────────
BG       = '#050d1a'
CARD_BG  = '#0d1f35'
ACCENT   = '#00d4aa'
BLUE     = '#0099ff'
ORANGE   = '#ff9900'
RED      = '#ff4444'
MUTED    = '#4a6fa5'
PLOT_BG  = '#0a1628'

def card(children, style={}):
    base = {'background':CARD_BG,'borderRadius':'16px','padding':'24px','marginBottom':'16px'}
    base.update(style)
    return html.Div(children, style=base)

def section_title(text):
    return html.P(text, style={
        'color':MUTED,'fontSize':'11px','letterSpacing':'3px',
        'textTransform':'uppercase','marginBottom':'16px',
        'borderLeft':f'3px solid {ACCENT}','paddingLeft':'12px'
    })

def kpi(label, value, unit, color, is_text=False):
    return html.Div([
        html.P(label, style={'color':MUTED,'fontSize':'11px','letterSpacing':'2px','textTransform':'uppercase','margin':'0 0 6px 0'}),
        html.H2(value if is_text else f"{value:.1f}",
                style={'color':color,'fontFamily':'Space Mono,monospace','fontSize':'38px','margin':'0 0 4px 0','fontWeight':'700'}),
        html.P(unit, style={'color':MUTED,'fontSize':'11px','margin':'0'})
    ], style={'background':CARD_BG,'borderRadius':'16px','padding':'24px','flex':'1',
              'textAlign':'center','minWidth':'180px'})

def slider_row(label, id, min, max, step, value, marks=None):
    return html.Div([
        html.Div([
            html.Span(label, style={'color':'white','fontSize':'13px','fontWeight':'600'}),
            html.Span(id=f'{id}-display', style={'color':ACCENT,'fontFamily':'Space Mono,monospace',
                                                   'fontSize':'13px','float':'right'})
        ], style={'marginBottom':'8px'}),
        dcc.Slider(id=id, min=min, max=max, step=step, value=value,
                   marks=marks or {min:str(min), max:str(max)},
                   tooltip={"placement":"bottom","always_visible":False},
                   updatemode='drag'),
    ], style={'marginBottom':'24px'})

app = Dash(__name__, suppress_callback_exceptions=True)
app.index_string = '''<!DOCTYPE html><html><head>{%metas%}<title>Greater Noida Water System</title>
{%favicon%}{%css%}
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap" rel="stylesheet">
<style>
* { box-sizing:border-box; margin:0; padding:0; }
body { background:#050d1a; font-family:"Syne",sans-serif; color:white; }
.tab-selected { background:#00d4aa !important; color:#050d1a !important; border-color:#00d4aa !important; font-weight:700 !important; }
</style></head><body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body></html>'''

app.layout = html.Div(style={'backgroundColor':BG,'minHeight':'100vh'}, children=[

    # ── Header ──────────────────────────────────────────
    html.Div(style={
        'background':f'linear-gradient(135deg,{BG} 0%,#0a1e38 50%,{BG} 100%)',
        'padding':'28px 40px','borderBottom':f'1px solid #0d2a4a',
        'display':'flex','justifyContent':'space-between','alignItems':'center'
    }, children=[
        html.Div([
            html.Div("SMART WATER SYSTEM", style={'color':ACCENT,'fontSize':'10px','letterSpacing':'4px','marginBottom':'6px'}),
            html.H1([html.Span("Greater Noida ",style={'color':'white'}),
                     html.Span("Water Intelligence",style={'color':MUTED})],
                    style={'fontSize':'30px','fontWeight':'800'}),
        ]),
        html.Div([
            html.Div(id='live-time', style={'color':ACCENT,'fontFamily':'Space Mono,monospace','fontSize':'12px','textAlign':'right','marginBottom':'6px'}),
            html.Span("● LIVE", style={'color':ACCENT,'fontSize':'11px','letterSpacing':'2px'})
        ])
    ]),

    # ── Alert Banner ────────────────────────────────────
    html.Div(id='alert-banner'),

    # ── KPI Row ─────────────────────────────────────────
    html.Div(id='kpi-row', style={'display':'flex','gap':'16px','padding':'24px 40px 0','flexWrap':'wrap'}),

    # ── Tabs ────────────────────────────────────────────
    html.Div(style={'padding':'24px 40px'}, children=[
        dcc.Tabs(id='tabs', value='monitoring', children=[
            dcc.Tab(label='📊 Live Monitoring', value='monitoring',
                    style={'backgroundColor':CARD_BG,'color':MUTED,'border':'none','borderRadius':'8px 8px 0 0','padding':'12px 20px'},
                    selected_style={'backgroundColor':ACCENT,'color':BG,'border':'none','borderRadius':'8px 8px 0 0','padding':'12px 20px','fontWeight':'700'}),
            dcc.Tab(label='🗺️ Flood Map', value='floodmap',
                    style={'backgroundColor':CARD_BG,'color':MUTED,'border':'none','borderRadius':'8px 8px 0 0','padding':'12px 20px','marginLeft':'4px'},
                    selected_style={'backgroundColor':ACCENT,'color':BG,'border':'none','borderRadius':'8px 8px 0 0','padding':'12px 20px','fontWeight':'700','marginLeft':'4px'}),
            dcc.Tab(label='💧 Recharge Calculator', value='recharge',
                    style={'backgroundColor':CARD_BG,'color':MUTED,'border':'none','borderRadius':'8px 8px 0 0','padding':'12px 20px','marginLeft':'4px'},
                    selected_style={'backgroundColor':ACCENT,'color':BG,'border':'none','borderRadius':'8px 8px 0 0','padding':'12px 20px','fontWeight':'700','marginLeft':'4px'}),
        ], style={'border':'none'}),

        html.Div(id='tab-content',
                 style={'background':CARD_BG,'borderRadius':'0 16px 16px 16px','padding':'28px','minHeight':'500px'})
    ]),

    html.Div("GREATER NOIDA SMART RAINWATER HARVESTING SYSTEM  ·  DATA: OPEN-METEO  ·  AUTO-REFRESH: 30s",
             style={'textAlign':'center','padding':'20px','color':'#1a3a5c',
                    'fontSize':'10px','letterSpacing':'2px','borderTop':'1px solid #0d2a4a'}),

    dcc.Interval(id='interval', interval=30000, n_intervals=0),
    dcc.Store(id='current-data')
])

# ── Main data callback ───────────────────────────────────
@app.callback(
    [Output('live-time','children'),
     Output('alert-banner','children'),
     Output('kpi-row','children'),
     Output('current-data','data')],
    Input('interval','n_intervals')
)
def update_header(n):
    now = datetime.now().strftime("%d %b %Y  %H:%M:%S IST")
    cur_water = float(df['water_level_cm'].iloc[-1])
    cur_rain  = float(df['rainfall_mm'].iloc[-1])
    cur_temp  = float(df['temp_c'].iloc[-1])

    if cur_water > 50:
        risk,rc  = 'HIGH', RED
        alert = html.Div('🚨  FLOOD ALERT — CRITICAL WATER LEVEL — EVACUATE LOW-LYING AREAS IMMEDIATELY',
            style={'padding':'16px 40px','textAlign':'center','fontSize':'14px','letterSpacing':'3px',
                   'fontWeight':'700','backgroundColor':'#2d0a0a','color':RED,'borderBottom':f'2px solid {RED}'})
    elif cur_water > 25:
        risk,rc  = 'MODERATE', ORANGE
        alert = html.Div('⚠️  FLOOD WARNING — WATER LEVELS RISING — MONITOR CLOSELY',
            style={'padding':'14px 40px','textAlign':'center','fontSize':'13px','letterSpacing':'3px',
                   'fontWeight':'700','backgroundColor':'#1a1400','color':ORANGE,'borderBottom':f'2px solid {ORANGE}'})
    else:
        risk,rc  = 'LOW', ACCENT
        alert = html.Div('✅  ALL CLEAR — NORMAL WATER CONDITIONS IN GREATER NOIDA',
            style={'padding':'12px 40px','textAlign':'center','fontSize':'12px','letterSpacing':'3px',
                   'fontWeight':'700','backgroundColor':'#001a12','color':ACCENT,'borderBottom':f'1px solid {ACCENT}33'})

    kpis = [
        kpi('Water Level', cur_water, 'CENTIMETRES', ACCENT),
        kpi('Rainfall',    cur_rain,  'MM / HOUR',   BLUE),
        kpi('Temperature', cur_temp,  'CELSIUS',     ORANGE),
        kpi('Flood Risk',  risk,      'CURRENT STATUS', rc, is_text=True),
    ]
    return now, alert, kpis, {'water':cur_water,'rain':cur_rain,'temp':cur_temp,'risk':risk}

# ── Tab content callback ─────────────────────────────────
@app.callback(
    Output('tab-content','children'),
    [Input('tabs','value'), Input('interval','n_intervals')]
)
def render_tab(tab, n):
    recent = df.tail(168)

    if tab == 'monitoring':
        # Combined chart
        combined = go.Figure()
        combined.add_trace(go.Bar(x=recent.index, y=recent['rainfall_mm'],
            name='Rainfall (mm)', marker_color='rgba(0,153,255,0.45)', yaxis='y2'))
        combined.add_trace(go.Scatter(x=recent.index, y=recent['water_level_cm'],
            name='Water Level (cm)', line=dict(color=ACCENT,width=3),
            fill='tozeroy', fillcolor='rgba(0,212,170,0.07)'))
        combined.add_hline(y=25, line_dash='dash', line_color=ORANGE, annotation_text='⚠ Moderate', annotation_font_color=ORANGE)
        combined.add_hline(y=50, line_dash='dash', line_color=RED, annotation_text='🚨 Flood', annotation_font_color=RED)
        combined.update_layout(
            paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG, height=420,
            font=dict(color=MUTED, family='Space Mono'),
            margin=dict(t=20,b=40,l=60,r=60), hovermode='x unified',
            legend=dict(bgcolor='rgba(0,0,0,0)'),
            xaxis=dict(gridcolor='#0d2a4a'),
            yaxis=dict(title='Water Level (cm)', gridcolor='#0d2a4a', color=ACCENT),
            yaxis2=dict(title='Rainfall (mm)', overlaying='y', side='right', color=BLUE, showgrid=False)
        )

        # Forecast
        cur_water = float(df['water_level_cm'].iloc[-1])
        cur_rain  = float(df['rainfall_mm'].iloc[-1])
        flevels, clevel = [], cur_water
        for _ in range(24):
            rf = max(0, np.random.normal(cur_rain*0.8, 0.05))
            nxt = max(0, 0.85*clevel + 0.60*rf + 0.10*float(df.iloc[-1]['soil_moisture']))
            flevels.append(nxt); clevel = nxt
        ftimes = pd.date_range(df.index[-1], periods=25, freq='h')[1:]

        forecast = go.Figure()
        forecast.add_trace(go.Scatter(x=recent.index[-72:], y=recent['water_level_cm'].iloc[-72:],
            name='Historical', line=dict(color=ACCENT,width=2)))
        forecast.add_trace(go.Scatter(x=ftimes, y=flevels,
            name='24hr Forecast', line=dict(color=ORANGE,width=2,dash='dot'),
            fill='tozeroy', fillcolor='rgba(255,153,0,0.06)'))
        forecast.add_hline(y=25, line_dash='dash', line_color=ORANGE)
        forecast.add_hline(y=50, line_dash='dash', line_color=RED)
        forecast.update_layout(
            paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG, height=360,
            font=dict(color=MUTED, family='Space Mono'),
            margin=dict(t=20,b=40,l=60,r=20), hovermode='x unified',
            legend=dict(bgcolor='rgba(0,0,0,0)'),
            xaxis=dict(gridcolor='#0d2a4a'),
            yaxis=dict(title='Water Level (cm)', gridcolor='#0d2a4a', color=ACCENT)
        )

        return html.Div([
            section_title('Water Level & Rainfall — Last 7 Days'),
            dcc.Graph(figure=combined, config={'displayModeBar':False}),
            html.Div(style={'height':'16px'}),
            section_title('24-Hour Water Level Forecast'),
            dcc.Graph(figure=forecast, config={'displayModeBar':False}),
        ])

    elif tab == 'floodmap':
        return html.Div([
            section_title('Greater Noida Flood Zone Map'),
            html.Div([
                html.Span("🔴 HIGH RISK", style={'color':RED,'marginRight':'20px','fontSize':'12px'}),
                html.Span("🟠 MODERATE",  style={'color':ORANGE,'marginRight':'20px','fontSize':'12px'}),
                html.Span("🟢 LOW RISK",  style={'color':'#00ff88','fontSize':'12px'}),
            ], style={'marginBottom':'14px'}),
            html.Iframe(srcDoc=map_html,
                style={'width':'100%','height':'600px','border':'none','borderRadius':'12px'})
        ])

    elif tab == 'recharge':
        return html.Div([
            section_title('Groundwater Recharge Calculator'),

            # Two column layout
            html.Div(style={'display':'flex','gap':'24px','flexWrap':'wrap'}, children=[

                # LEFT — Sliders
                html.Div(style={'flex':'1','minWidth':'280px'}, children=[
                    html.P("Adjust parameters to simulate recharge potential",
                           style={'color':MUTED,'fontSize':'12px','marginBottom':'24px'}),

                    slider_row("📍 Total Area (km²)", 'slider-area', 100, 985, 10, 985,
                               {100:'100',985:'985 (Full GN)'}),
                    slider_row("🌧️ Annual Rainfall (mm)", 'slider-rain', 200, 1200, 10, 624,
                               {200:'Dry',624:'Normal',1200:'Flood yr'}),
                    slider_row("🏙️ Urban Area (%)", 'slider-urban', 10, 90, 5, 60,
                               {10:'10%',60:'Current',90:'90%'}),
                    slider_row("🌱 Harvesting Efficiency (%)", 'slider-efficiency', 1, 60, 1, 35,
                               {1:'None',35:'With pits',60:'Optimised'}),
                    slider_row("👥 Population to Supply", 'slider-pop', 10000, 2000000, 10000, 350000,
                               {10000:'10K',350000:'GN Now',2000000:'2M'}),

                    html.Button("⚡ Calculate Recharge", id='calc-btn',
                        style={'width':'100%','padding':'14px','background':ACCENT,
                               'color':BG,'border':'none','borderRadius':'10px',
                               'fontSize':'14px','fontWeight':'700','cursor':'pointer',
                               'marginTop':'8px','letterSpacing':'1px'})
                ]),

                # RIGHT — Results
                html.Div(id='recharge-results',
                         style={'flex':'1','minWidth':'280px'})
            ])
        ])

# ── Recharge calculator callback ─────────────────────────
@app.callback(
    Output('recharge-results','children'),
    Input('calc-btn','n_clicks'),
    [State('slider-area','value'),
     State('slider-rain','value'),
     State('slider-urban','value'),
     State('slider-efficiency','value'),
     State('slider-pop','value')],
    prevent_initial_call=False
)
def calculate_recharge(n, area_km2, rainfall_mm, urban_pct, efficiency_pct, population):
    area_m2          = (area_km2 or 985) * 1_000_000
    rainfall         = rainfall_mm or 624
    urban            = (urban_pct or 60) / 100
    agri             = min(1-urban, 0.25)
    wetland          = max(1-urban-agri, 0)
    efficiency       = (efficiency_pct or 35) / 100
    pop              = population or 350000

    # Water balance
    total_rain_L     = rainfall * area_m2 / 1000
    natural_perc     = (urban*0.001 + agri*0.35 + wetland*0.60)
    natural_L        = total_rain_L * natural_perc
    with_system_L    = total_rain_L * efficiency
    extra_L          = with_system_L - natural_L
    runoff_saved_L   = total_rain_L - with_system_L
    days_supply      = with_system_L / (pop * 150) if pop > 0 else 0
    improvement      = with_system_L / natural_L if natural_L > 0 else 0

    def result_card(label, value, unit, color, big=False):
        return html.Div([
            html.P(label, style={'color':MUTED,'fontSize':'10px','letterSpacing':'2px',
                                 'textTransform':'uppercase','margin':'0 0 4px 0'}),
            html.H3(value, style={'color':color,'fontFamily':'Space Mono,monospace',
                                  'fontSize':'28px' if big else '22px','margin':'0 0 2px 0','fontWeight':'700'}),
            html.P(unit, style={'color':MUTED,'fontSize':'11px','margin':'0'})
        ], style={'background':'#071428','borderRadius':'12px','padding':'16px',
                  'border':f'1px solid {color}33','marginBottom':'12px'})

    # Recharge bar chart
    fig = go.Figure()
    categories = ['Total Rainfall', 'Natural Recharge\n(no system)', 'With Harvesting\nSystem', 'Wasted Runoff']
    values     = [total_rain_L/1e6, natural_L/1e6, with_system_L/1e6, runoff_saved_L/1e6]
    colors_bar = [BLUE, RED, ACCENT, ORANGE]
    fig.add_trace(go.Bar(x=categories, y=values, marker_color=colors_bar,
                         text=[f'{v:.1f}M L' for v in values],
                         textposition='outside', textfont=dict(color='white',size=11)))
    fig.update_layout(
        paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG, height=300,
        font=dict(color=MUTED, family='Space Mono'),
        margin=dict(t=20,b=60,l=40,r=20),
        yaxis=dict(title='Million Litres', gridcolor='#0d2a4a'),
        xaxis=dict(gridcolor='rgba(0,0,0,0)'),
        showlegend=False
    )

    return html.Div([
        html.Div(style={'display':'grid','gridTemplateColumns':'1fr 1fr','gap':'12px','marginBottom':'16px'}, children=[
            result_card('Total Rainfall Volume',  f"{total_rain_L/1e6:.1f}M",  'Litres',         BLUE,  True),
            result_card('Natural Recharge',        f"{natural_L/1e6:.2f}M",    'Litres (no sys)', RED),
            result_card('With Harvesting System',  f"{with_system_L/1e6:.1f}M",'Litres',         ACCENT,True),
            result_card('Improvement',             f"{improvement:.0f}x",       'Better than natural', ORANGE),
        ]),
        result_card('Days of Water Supply',
                    f"{days_supply:.0f} days",
                    f"for {pop:,} people at 150L/day", ACCENT, True),
        section_title('Volume Comparison'),
        dcc.Graph(figure=fig, config={'displayModeBar':False})
    ])

if __name__ == '__main__':
    print("Dashboard: http://127.0.0.1:8050")
    app.run(debug=False)
