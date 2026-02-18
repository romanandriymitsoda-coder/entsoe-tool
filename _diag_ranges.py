import pandas as pd
from datetime import datetime
import export_combined_excel as mod
start = datetime(2025,10,1)
end = datetime(2025,10,31)
cz,de,pl,at = mod.get_energy_dfs3('sample_data', start, end)
for name,df in [('CZ',cz),('DE',de),('AT',at)]:
    if not df.empty:
        print(name, df['ISP(UTC)'].min(), df['ISP(UTC)'].max())
        print(name, df['ISP(UTC)'].head(3).tolist())
