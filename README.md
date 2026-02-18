# ENTSO-E File Library Downloader

Desktop Python tool for downloading balancing market data from the ENTSO-E Transparency Platform File Library and exporting cleaned monthly outputs to Excel.

## What this project does

This app provides a GUI workflow to:

- Download selected datasets from ENTSO-E File Library by month range.
- Filter and normalize balancing reserve and balancing energy records.
- Aggregate hourly values.
- Export a combined Excel report with country sheets and daily averages.

## Data sources used

The downloader calls ENTSO-E File Library APIs and currently targets:

- `AmountAndPricesPaidOfBalancingReservesUnderContract_17.1.B_C_r3`
- `PricesOfActivatedBalancingEnergy_17.1.F_r3`

Authentication is done via Keycloak token endpoint:

- `https://keycloak.tp.entsoe.eu/realms/tp/protocol/openid-connect/token`

## Output

The app generates files like:

- `regulacni_zalohy_a_energie_YYYY-MM-DD_HH-MM.xlsx`

Workbook content:

- Country sheets: `CZ`, `DE`, `PL`, `AT`, `SK`
- Daily average sheets: `<COUNTRY> - denni prumery`

## Main features

- Tkinter desktop GUI (dataset selection, period selection, settings).
- Month-range download filter (`YYYY_MM` matching in filenames).
- Automatic token retrieval and API file download.
- Country-level reshaping/aggregation of reserve and energy price data.
- Merged output table by `ISP(UTC)` and daily averages.

## Tech stack

- Python
- `tkinter` (GUI)
- `requests` (API communication)
- `pandas` (data processing)
- `openpyxl` (Excel export engine)

## Quick start

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
pip install pandas requests openpyxl
```

4. Create `settings.json` from `settings.example.json` and fill in `host`, `username`, `password`, and `download_path`.
5. Run the app:

```bash
python main.py
```

## Security note

- `settings.json` contains credentials and is intentionally git-ignored.
- Never commit real usernames/passwords to a public repository.

## Project structure

- `main.py` - GUI app, API calls, download orchestration.
- `export_combined_excel.py` - parsing, filtering, aggregation, Excel export.
- `sample_data/` - sample CSV files.
- `hooks/`, `*.spec`, `tools/` - build/packaging helpers.


