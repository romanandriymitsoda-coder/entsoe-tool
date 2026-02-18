$lines = Get-Content export_combined_excel.py
for ($i=179; $i -lt [Math]::Min($lines.Length, 230); $i++) { '{0,4}: {1}' -f ($i+1), $lines[$i] }
