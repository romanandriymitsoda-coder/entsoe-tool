from datetime import datetime
import export_combined_excel as mod
print('Testing get_reserves_dfs on sample_data (may be empty for SK):')
cz,de,pl,at,sk = mod.get_reserves_dfs('sample_data', datetime(2025,10,1), datetime(2025,10,31))
print('reserves CZ/DE/PL/AT/SK rows:', len(cz), len(de), len(pl), len(at), len(sk))
print('Testing get_energy_dfs on sample_data:')
cz,de,pl,at,sk = mod.get_energy_dfs('sample_data', datetime(2025,10,1), datetime(2025,10,31))
print('energy CZ/DE/PL/AT/SK rows:', len(cz), len(de), len(pl), len(at), len(sk))
