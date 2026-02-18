$lines = Get-Content export_combined_excel.py
for ($i=120; $i -le 146; $i++) { '{0,4}: {1}' -f ($i+1), $lines[$i] }
