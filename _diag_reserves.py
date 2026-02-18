import pandas as pd
path = r'sample_data/2025_10_AmountAndPricesPaidOfBalancingReservesUnderContract_17.1.B_C_r3 (3).csv'
df = pd.read_csv(path, sep='\t')
df['ISP(UTC)'] = pd.to_datetime(df['ISP(UTC)'], errors='coerce')
print('reserves minmax', df['ISP(UTC)'].min(), df['ISP(UTC)'].max())
print('DE codes sample:', df[df['AreaMapCode'].astype(str).str.startswith('DE')]['AreaMapCode'].dropna().unique()[:10])
