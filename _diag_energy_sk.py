from datetime import datetime
import export_combined_excel as mod
start = datetime(2025,10,1)
end = datetime(2025,10,31)
cz,de,pl,at,sk = mod.get_energy_dfs('sample_data', start, end)
print('SK rows:', len(sk))
if len(sk):
    print('SK min/max:', sk['ISP(UTC)'].min(), sk['ISP(UTC)'].max())
