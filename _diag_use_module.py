import pandas as pd
from datetime import datetime
import export_combined_excel as mod
start = datetime(2025,10,1)
end = datetime(2025,10,31)
cz,de,pl,at = mod.get_energy_dfs3('sample_data', start, end)
for name,df in [('CZ',cz),('DE',de),('AT',at)]:
    print(name, 'rows:', len(df), 'cols:', list(df.columns))
    w = df[(df['ISP(UTC)']>='2025-10-23 05:00:00')&(df['ISP(UTC)']<='2025-10-23 21:00:00')]
    print(name, 'window rows:', len(w))
    print(w.head())
