import requests, json, os

def get_live_weather():
    try:
        r = requests.get('https://api.open-meteo.com/v1/forecast',
            params={
                'latitude': 28.4744, 'longitude': 77.5040,
                'current': 'temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code',
                'daily':   'temperature_2m_max,temperature_2m_min,precipitation_sum',
                'timezone':'Asia/Kolkata', 'forecast_days': 7
            }, timeout=10)
        if r.status_code == 200:
            data = r.json()
            os.makedirs('data', exist_ok=True)
            with open('data/realtime_weather.json', 'w') as f:
                json.dump(data, f)
            return data
    except Exception as e:
        print(f"Weather fetch failed: {e}")
    # fallback to cached
    if os.path.exists('data/realtime_weather.json'):
        return json.load(open('data/realtime_weather.json'))
    return None

def parse_weather(data):
    if not data: return {}
    cur = data.get('current', {})
    daily = data.get('daily', {})
    code = cur.get('weather_code', 0)
    if code == 0:               icon = '☀️'
    elif code in range(1,4):    icon = '🌤️'
    elif code in range(51,68):  icon = '🌧️'
    elif code in range(71,78):  icon = '❄️'
    elif code in range(80,83):  icon = '⛈️'
    else:                       icon = '🌥️'
    return {
        'temp':      cur.get('temperature_2m', 0),
        'humidity':  cur.get('relative_humidity_2m', 0),
        'rain':      cur.get('precipitation', 0),
        'wind':      cur.get('wind_speed_10m', 0),
        'icon':      icon,
        'time':      cur.get('time', ''),
        'forecast':  daily,
    }

if __name__ == '__main__':
    data = get_live_weather()
    w = parse_weather(data)
    print(f"\n{'='*40}")
    print(f"  {w['icon']} Greater Noida — LIVE")
    print(f"{'='*40}")
    print(f"  Temperature : {w['temp']}°C")
    print(f"  Humidity    : {w['humidity']}%")
    print(f"  Rainfall    : {w['rain']} mm")
    print(f"  Wind        : {w['wind']} km/h")
    print(f"  Updated     : {w['time']}")
    print(f"{'='*40}")
    if w['forecast']:
        print("\n  7-Day Forecast:")
        for i in range(7):
            print(f"  {w['forecast']['time'][i]}  "
                  f"{w['forecast']['precipitation_sum'][i] or 0:.1f}mm  "
                  f"{w['forecast']['temperature_2m_max'][i]:.0f}°/"
                  f"{w['forecast']['temperature_2m_min'][i]:.0f}°")
