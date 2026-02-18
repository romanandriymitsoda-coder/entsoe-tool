$lines = Get-Content export_combined_excel.py
for ($i=0; $i -lt $lines.Length; $i++) {
  if ($lines[$i] -match '^def get_energy_dfs') { $start = $i }
  if ($lines[$i] -match '^def reshape_energy_data') { $end = $i }
}
for ($j=$start; $j -lt $end; $j++) { '{0,4}: {1}' -f ($j+1), $lines[$j] }
