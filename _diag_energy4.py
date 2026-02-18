from datetime import datetime
import export_combined_excel as mod
start = datetime(2025,10,1)
end = datetime(2025,10,31)
cz,de,pl,at = mod.get_energy_dfs('sample_data', start, end)
for name,df in [('CZ',cz),('DE',de),('PL',pl),('AT',at)]:
    print(name, 'rows:', len(df))
    if not df.empty:
        print(name, 'min/max:', df['ISP(UTC)'].min(), df['ISP(UTC)'].max())
