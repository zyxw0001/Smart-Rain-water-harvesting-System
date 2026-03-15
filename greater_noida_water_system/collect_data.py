import requests, pandas as pd, numpy as np, time, os, calendar

LAT, LON = 28.4744, 77.5040

def fetch_data():
    all_data = []
    chunks = [(1984,2013),(2014,2024)]
    for sy,ey in chunks:
        print(f'Fetching {sy}-{ey}...', end=' ', flush=True)
        r = requests.get('https://power.larc.nasa.gov/api/temporal/monthly/point',
            params={'parameters':'PRECTOTCORR,T2M,RH2M,GWETROOT','community':'RE',
                    'longitude':LON,'latitude':LAT,'start':str(sy),'end':str(ey),'format':'JSON'},
            timeout=60)
        if r.status_code == 200:
            props = r.json()['properties']['parameter']
            rain=props['PRECTOTCORR']; temp=props.get('T2M',{}); humid=props.get('RH2M',{}); soil=props.get('GWETROOT',{})
            for ym,val in rain.items():
                month = int(ym[4:])
                if month > 12 or val in [-999,-99]:
                    continue
                days = calendar.monthrange(int(ym[:4]), month)[1]
                all_data.append({'year':int(ym[:4]),'month':month,
                    'rainfall_mm':round(float(val)*days,2),
                    'temp_c':round(float(temp.get(ym,25)),2),
                    'humidity_pct':round(float(humid.get(ym,60)),2),
                    'soil_moisture':round(float(soil.get(ym,0.3)),4),
                    'source':'NASA'})
            print(f'OK ({len(all_data)} total)')
        time.sleep(2)

    # Synthetic backfill 1924-1983
    np.random.seed(42)
    monthly_avg_mm = [15,18,14,8,20,65,210,195,120,30,8,10]
    for year in range(1924,1984):
        for month in range(1,13):
            base = monthly_avg_mm[month-1]
            all_data.append({'year':year,'month':month,
                'rainfall_mm':round(max(0, base+np.random.normal(0,base*0.35)),2),
                'temp_c':round(15+15*np.sin((month-3)*np.pi/6)+np.random.normal(0,1.5),2),
                'humidity_pct':round(55+(month in [7,8,9])*25+np.random.normal(0,5),2),
                'soil_moisture':round(0.2+(month in [7,8,9])*0.2+np.random.normal(0,0.03),4),
                'source':'synthetic'})

    df = pd.DataFrame(all_data).sort_values(['year','month']).reset_index(drop=True)
    os.makedirs('data', exist_ok=True)
    df.to_csv('data/100yr_complete.csv', index=False)
    df.groupby('year').agg(rainfall_mm=('rainfall_mm','sum')).reset_index().to_csv('data/100yr_annual.csv', index=False)
    print(f'Done — {len(df)} months saved.')
    return df

if __name__ == '__main__':
    fetch_data()
