from datetime import datetime
import export_combined_excel as mod
start = datetime(2025,10,23)
end = datetime(2025,10,23)
cz,de,pl,at = mod.get_energy_dfs('sample_data', start, end)
for name,df in [('CZ',cz),('DE',de),('AT',at)]:
    print(name, 'rows:', len(df))
    if len(df):
        print(name, 'min/max:', df['ISP(UTC)'].min(), df['ISP(UTC)'].max())
        w = df[(df['ISP(UTC)']>='2025-10-23 05:00:00')&(df['ISP(UTC)']<='2025-10-23 21:00:00')]
        print(name, 'window rows:', len(w))
