$i=0; $lines = Get-Content export_combined_excel.py; 
for($i=0;$i -lt $lines.Length;$i++){
  if($lines[$i] -match '^def '){ '{0,4}: {1}' -f ($i+1), $lines[$i] }
}
