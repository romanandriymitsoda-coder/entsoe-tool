import pandas as pd
p='sample_data/2025_10_PricesOfActivatedBalancingEnergy_17.1.F_r3 (1).csv'
df=pd.read_csv(p,sep='\t')
df['ISP(UTC)']=pd.to_datetime(df['ISP(UTC)'],errors='coerce')
sel=df[(df['ISP(UTC)']>='2025-10-23 10:00:00')&(df['ISP(UTC)']<='2025-10-23 11:00:00')]
print(sel[sel['MapCode'].isin(['CZ','AT','DE','DE-LU','DE_LU','DE_TransnetBW'])].head(10))
print('Any CZ rows in that hour?', (sel['MapCode']=='CZ').any())
print('Unique mapcodes in that hour that start DE:', sel['MapCode'].dropna().astype(str).str.startswith('DE').sum())
