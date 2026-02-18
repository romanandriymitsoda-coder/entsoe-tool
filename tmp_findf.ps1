$lines = Get-Content export_combined_excel.py
for ($i=0; $i -lt $lines.Length; $i++) {
  if ($lines[$i] -match '^def get_reserves_dfs') { Write-Output ("export_combined_excel.py:" + ($i+1)) }
  if ($lines[$i] -match '^def aggregate_hourly') { Write-Output ("export_combined_excel.py:" + ($i+1)) }
}
