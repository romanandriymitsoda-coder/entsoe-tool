import pandas as pd
path = r'sample_data/2025_10_PricesOfActivatedBalancingEnergy_17.1.F_r3 (1).csv'
df = pd.read_csv(path, sep='\t')
df['ISP(UTC)'] = pd.to_datetime(df['ISP(UTC)'], errors='coerce')
df = df.dropna(subset=['ISP(UTC)'])
mask = (df['ISP(UTC)']>= '2025-10-23 05:00:00') & (df['ISP(UTC)']<= '2025-10-23 21:00:00')
dfw = df[mask]
print('Rows in window:', len(dfw))
print('MapCodes in window for CZ/DE/AT:')
print(dfw[dfw['MapCode'].isin(['CZ','AT','DE','DE-LU','DE_LU','DE_TransnetBW'])]['MapCode'].value_counts())
print('MapCodes starting with DE in window:')
print(dfw[dfw['MapCode'].astype(str).str.startswith('DE')]['MapCode'].value_counts().head(10))
for mc in ['CZ','AT']:
    t = dfw[dfw['MapCode']==mc]['TypeOfProduct'].value_counts(dropna=False)
    print(mc,'TypeOfProduct counts:', dict(t))
cols = ['NotSpecifiedUpPrice','NotSpecifiedDownPrice','GenerationUpPrice','GenerationDownPrice','LoadUpPrice','LoadDownPrice']
for mc in ['CZ','AT']:
    print('\n--', mc)
    d = dfw[dfw['MapCode']==mc]
    for c in cols:
        if c in d.columns:
            print(c, d[c].notna().sum())
print('\n-- DE TSO mapcodes')
ded = dfw[dfw['MapCode'].astype(str).str.startswith('DE')]
for c in cols:
    if c in ded.columns:
        print(c, ded[c].notna().sum())
for mc in ['CZ','AT']:
    print('\n', mc, 'ReserveType distribution:')
    x = dfw[dfw['MapCode']==mc]['ReserveType'].value_counts()
    print(x)
