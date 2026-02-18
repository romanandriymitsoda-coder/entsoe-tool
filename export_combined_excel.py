import pandas as pd
import os
from datetime import datetime

def _next_month(dt: datetime) -> datetime:
    if dt.month == 12:
        return datetime(dt.year + 1, 1, 1)
    return datetime(dt.year, dt.month + 1, 1)

def export_combined_excel(folder_path, period_start: datetime | None = None, period_end: datetime | None = None):
    # Normalize month bounds if provided: [start, end_exclusive)
    start_bound = end_exclusive = None
    if period_start is not None and period_end is not None:
        start_bound = datetime(period_start.year, period_start.month, 1)
        end_exclusive = _next_month(datetime(period_end.year, period_end.month, 1))

    reserves_cz, reserves_de, reserves_pl, reserves_at, reserves_sk = get_reserves_dfs(folder_path, start_bound, end_exclusive)
    energy_cz, energy_de, energy_pl, energy_at, energy_sk = get_energy_dfs(folder_path, start_bound, end_exclusive)

    if all(df.empty for df in [
        reserves_cz, reserves_de, reserves_pl, reserves_at, reserves_sk,
        energy_cz, energy_de, energy_pl, energy_at, energy_sk
    ]):
        return None

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_path = os.path.join(folder_path, f"regulacni_zalohy_a_energie_{timestamp}.xlsx")

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for code, res_df, en_df in [
            ("CZ", reserves_cz, energy_cz),
            ("DE", reserves_de, energy_de),
            ("PL", reserves_pl, energy_pl),
            ("AT", reserves_at, energy_at),
            ("SK", reserves_sk, energy_sk),
        ]:
            if not res_df.empty or not en_df.empty:
                merged = merge_tables(res_df, en_df)
                if merged.empty:
                    merged = res_df if not res_df.empty else en_df
                merged.to_excel(writer, sheet_name=code, index=False)
                if not merged.empty and "ISP(UTC)" in merged.columns:
                    daily_avg = compute_daily_averages(merged)
                    daily_avg.to_excel(writer, sheet_name=f"{code} - denní průměry", index=False)

    return output_path

def get_reserves_dfs(folder_path, start_bound: datetime | None = None, end_exclusive: datetime | None = None):
    # New ENTSO-E schema introduces AreaMapCode and InstanceCode.
    # Read header from file (robust to both old and new schemas) and normalize.
    wanted_reserve_types = {
        "Manual Frequency Restoration Reserve (mFRR)",
        "Automatic Frequency Restoration Reserve (aFRR)",
        "Frequency Containment Reserve (FCR)"
    }
    file_names = [
        f for f in os.listdir(folder_path)
        if "AmountAndPricesPaidOfBalancingReservesUnderContract" in f and f.endswith(".csv")
    ]
    file_paths = [os.path.join(folder_path, f) for f in file_names]
    df_list = []

    for file in file_paths:
        try:
            df = pd.read_csv(file, sep="\t", header=0)
            # Normalize column names to handle both old and new schemas
            rename_map = {
                "MapCode": "AreaMapCode",
                "UpdateTime": "UpdateTime(UTC)",
                "AreaName": "AreaDisplayName",
            }
            df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

            # Filter wanted reserve types and countries with their respective rules
            # TypeOfProduct logic reverted to original behavior:
            # - CZ/DE/AT: require "Standard"
            # - PL:       missing (NaN)
            cz_codes = ["CZ", "CZ-CEPS", "CZ_CEPS", "CZ_CEPS_SCA"]
            de_codes = ["DE_TransnetBW_SCA", "DE_TransnetBW", "DE_50HzT", "DE_TenneT_GER", "DE_Amprion", "DE", "DE-LU", "DE_LU"]
            at_codes = ["AT", "AT-APG", "AT_APG", "AT_APG_SCA"]
            sk_codes = ["SK", "SK-SEPS", "SK_SEPS", "SK_SEPS_SCA"]
            df = df[
                df["ReserveType"].isin(wanted_reserve_types) &
                (
                    ((df["AreaMapCode"].isin(cz_codes + de_codes + at_codes + sk_codes)) &
                     (df["TimeHorizon"] == "Daily") &
                     (df["TypeOfProduct"] == "Standard"))
                    |
                    ((df["AreaMapCode"] == "PL") &
                     (df["TimeHorizon"] == "Hourly") &
                     (df["TypeOfProduct"].isna()))
                )
            ]
            df["ISP(UTC)"] = pd.to_datetime(df["ISP(UTC)"])
            if start_bound is not None and end_exclusive is not None:
                df = df[(df["ISP(UTC)"] >= start_bound) & (df["ISP(UTC)"] < end_exclusive)]
            df_list.append(df)
        except Exception as e:
            print(f"❌ Chyba při zpracování souboru {file}: {e}")

    if df_list:
        merged_df = pd.concat(df_list, ignore_index=True)
        return (
            aggregate_hourly(merged_df, ["CZ", "CZ-CEPS", "CZ_CEPS", "CZ_CEPS_SCA"]),
            aggregate_hourly(merged_df, ["DE_TransnetBW_SCA", "DE_TransnetBW", "DE_50HzT", "DE_TenneT_GER", "DE_Amprion", "DE", "DE-LU", "DE_LU"]),
            aggregate_hourly(merged_df, ["PL"]),
            aggregate_hourly(merged_df, ["AT", "AT-APG", "AT_APG", "AT_APG_SCA"]),
            aggregate_hourly(merged_df, ["SK", "SK-SEPS", "SK_SEPS", "SK_SEPS_SCA"]),
        )
    else:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def get_energy_dfs(folder_path, start_bound: datetime | None = None, end_exclusive: datetime | None = None):
    column_names = [
        "ISP(UTC)", "ResolutionCode", "AreaCode", "AreaDisplayName", "AreaTypeCode",
        "MapCode", "ReserveType", "TypeOfProduct",
        "LoadUpPrice", "LoadDownPrice", "GenerationUpPrice", "GenerationDownPrice",
        "NotSpecifiedUpPrice", "NotSpecifiedDownPrice", "PriceType", "Currency", "UpdateTime"
    ]
    wanted_reserve_types = {
        "Manual Frequency Restoration Reserve (mFRR)",
        "Automatic Frequency Restoration Reserve (aFRR)"
    }
    file_names = [
        f for f in os.listdir(folder_path)
        if "PricesOfActivatedBalancingEnergy" in f and f.endswith(".csv")
    ]
    file_paths = [os.path.join(folder_path, f) for f in file_names]
    df_list = []

    for file in file_paths:
        try:
            df = pd.read_csv(file, sep="\t", names=column_names, header=None, skiprows=1)
            df = df[
                df["ReserveType"].isin(wanted_reserve_types) &
                (
                    ((df["MapCode"].isin(["CZ", "DE_TransnetBW", "DE", "DE-LU", "DE_LU", "DE_50HzT", "DE_TenneT_GER", "DE_Amprion", "AT"])) &
                     (df["TypeOfProduct"] == "Standard"))
                    |
                    ((df["MapCode"] == "PL") & (df["TypeOfProduct"] == "Not Specified"))
                    |
                    ((df["MapCode"] == "SK") & (df["TypeOfProduct"] == "Specific"))
                )
            ]
            df["ISP(UTC)"] = pd.to_datetime(df["ISP(UTC)"])
            if start_bound is not None and end_exclusive is not None:
                df = df[(df["ISP(UTC)"] >= start_bound) & (df["ISP(UTC)"] < end_exclusive)]
            df_list.append(df)
        except Exception as e:
            print(f"❌ Chyba při zpracování souboru {file}: {e}")

    if df_list:
        merged_df = pd.concat(df_list, ignore_index=True)
        return (
            reshape_energy_data(merged_df, ["CZ"]),
            reshape_energy_data(merged_df, ["DE_TransnetBW", "DE", "DE-LU", "DE_LU", "DE_50HzT", "DE_TenneT_GER", "DE_Amprion", "DE(Amprion)_LU"]),
            reshape_energy_data(merged_df, ["PL"]),
            reshape_energy_data(merged_df, ["AT"]),
            reshape_energy_data(merged_df, ["SK"]),
        )
    else:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


def get_energy_dfs2(folder_path, start_bound: datetime | None = None, end_exclusive: datetime | None = None):
    column_names = [
        "ISP(UTC)", "ResolutionCode", "AreaCode", "AreaDisplayName", "AreaTypeCode",
        "MapCode", "ReserveType", "TypeOfProduct",
        "LoadUpPrice", "LoadDownPrice", "GenerationUpPrice", "GenerationDownPrice",
        "NotSpecifiedUpPrice", "NotSpecifiedDownPrice", "PriceType", "Currency", "UpdateTime"
    ]
    wanted_reserve_types = {
        "Manual Frequency Restoration Reserve (mFRR)",
        "Automatic Frequency Restoration Reserve (aFRR)"
    }
    file_names = [
        f for f in os.listdir(folder_path)
        if "PricesOfActivatedBalancingEnergy" in f and f.endswith(".csv")
    ]
    file_paths = [os.path.join(folder_path, f) for f in file_names]
    df_list = []

    for file in file_paths:
        try:
            df = pd.read_csv(file, sep="\t", names=column_names, header=None, skiprows=1)
            # Minimal change: include German TSO-level MapCodes while keeping classic product rules
            de_codes = [
                "DE_TransnetBW", "DE", "DE-LU", "DE_LU",
                "DE_50HzT", "DE_TenneT_GER", "DE_Amprion", "DE(Amprion)_LU"
            ]
            keep_codes = ["CZ", "AT", "PL"] + de_codes
            df = df[
                df["ReserveType"].isin(wanted_reserve_types) &
                (df["MapCode"].isin(keep_codes)) &
                (
                    ((df["MapCode"].isin(["CZ", "DE_TransnetBW", "DE", "DE-LU", "DE_LU", "DE_50HzT", "DE_TenneT_GER", "DE_Amprion", "DE(Amprion)_LU", "AT"])) &
                     (df["TypeOfProduct"] == "Standard"))
                    |
                    ((df["MapCode"] == "PL") & (df["TypeOfProduct"] == "Not Specified"))
                )
            ]
            df["ISP(UTC)"] = pd.to_datetime(df["ISP(UTC)"])
            if start_bound is not None and end_exclusive is not None:
                df = df[(df["ISP(UTC)"] >= start_bound) & (df["ISP(UTC)"] < end_exclusive)]
            df_list.append(df)
        except Exception as e:
            print(f"��� Chyba p�ti zpracov��n�� souboru {file}: {e}")

    if df_list:
        merged_df = pd.concat(df_list, ignore_index=True)
        return (
            reshape_energy_data(merged_df, ["CZ"]),
            reshape_energy_data(merged_df, ["DE_TransnetBW", "DE", "DE-LU", "DE_LU", "DE_50HzT", "DE_TenneT_GER", "DE_Amprion", "DE(Amprion)_LU"]),
            reshape_energy_data(merged_df, ["PL"]),
            reshape_energy_data(merged_df, ["AT"]),
        )
    else:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


def get_energy_dfs3(folder_path, start_bound: datetime | None = None, end_exclusive: datetime | None = None):
    column_names = [
        "ISP(UTC)", "ResolutionCode", "AreaCode", "AreaDisplayName", "AreaTypeCode",
        "MapCode", "ReserveType", "TypeOfProduct",
        "LoadUpPrice", "LoadDownPrice", "GenerationUpPrice", "GenerationDownPrice",
        "NotSpecifiedUpPrice", "NotSpecifiedDownPrice", "PriceType", "Currency", "UpdateTime"
    ]
    file_names = [
        f for f in os.listdir(folder_path)
        if "PricesOfActivatedBalancingEnergy" in f and f.endswith(".csv")
    ]
    file_paths = [os.path.join(folder_path, f) for f in file_names]
    df_list = []

    for file in file_paths:
        try:
            df = pd.read_csv(file, sep="\t", names=column_names, header=None, skiprows=1)
            # Accept any ReserveType mentioning aFRR/mFRR (covers LS/DA/SA variants)
            rt_mask = df["ReserveType"].astype(str).str.contains(r"aFRR|mFRR", case=False, regex=True)
            mc = df["MapCode"].astype(str)
            # Countries: CZ, AT, PL; Germany: any code starting with DE (TSO-level, DE-LU variants included)
            map_mask = mc.isin(["CZ", "AT", "PL"]) | mc.str.startswith("DE")
            # Product types for energy: allow Standard/Not Specified/empty (do not change reserves rules)
            tp_mask = df["TypeOfProduct"].astype(str).isin(["Standard", "Not Specified"]) | df["TypeOfProduct"].isna()
            df = df[rt_mask & map_mask & tp_mask]
            df["ISP(UTC)"] = pd.to_datetime(df["ISP(UTC)"])
            if start_bound is not None and end_exclusive is not None:
                df = df[(df["ISP(UTC)"] >= start_bound) & (df["ISP(UTC)"] < end_exclusive)]
            df_list.append(df)
        except Exception as e:
            print(f"Chyba při zpracování souboru {file}: {e}")

    if not df_list:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    merged_df = pd.concat(df_list, ignore_index=True)
    # Build dynamic German code set from data
    de_codes = sorted({c for c in merged_df["MapCode"].astype(str).unique() if str(c).startswith("DE")})
    return (
        reshape_energy_data(merged_df, ["CZ"]),
        reshape_energy_data(merged_df, de_codes),
        reshape_energy_data(merged_df, ["PL"]),
        reshape_energy_data(merged_df, ["AT"]),
    )

def aggregate_hourly(df, mapcodes):
    # mapcodes can be a single code or a list
    if isinstance(mapcodes, str):
        codes = [mapcodes]
    else:
        codes = list(mapcodes)
    df = df[df["AreaMapCode"].isin(codes)].copy()
    if df.empty:
        return pd.DataFrame()
    # Normalize values
    df["ReserveType"] = df["ReserveType"].astype(str).str.strip()
    # Normalize direction variants
    dir_norm = (
        df["Direction"].astype(str).str.strip().str.lower()
        .replace({
            "up": "up", "upward": "up", "upwards": "up", "+": "up",
            "down": "down", "downward": "down", "downwards": "down", "-": "down"
        })
    )
    df["Direction"] = dir_norm.str.title().replace({"Up": "Up", "Down": "Down"})
    # Ensure price numeric
    df["Price(MW/ISP)"] = pd.to_numeric(df["Price(MW/ISP)"], errors="coerce")
    df["Hour"] = df["ISP(UTC)"].dt.floor("h")
    df["Multiplier"] = df["ResolutionCode"].map({"PT15M": 4, "PT30M": 2, "PT60M": 1}).fillna(1)
    df["AdjustedPrice"] = df["Price(MW/ISP)"] * df["Multiplier"]
    fcr = df[df["ReserveType"] == "Frequency Containment Reserve (FCR)"]
    fcr_avg = fcr.groupby("Hour")["AdjustedPrice"].mean()
    pivot = pd.pivot_table(
        df[df["ReserveType"] != "Frequency Containment Reserve (FCR)"],
        values="AdjustedPrice",
        index="Hour",
        columns=["ReserveType", "Direction"],
        aggfunc="mean"
    )
    result = pd.DataFrame(index=pivot.index)
    result["aFRR+ RZ [(EUR/MW)/h]"] = pivot.get(("Automatic Frequency Restoration Reserve (aFRR)", "Up"))
    result["aFRR- RZ [(EUR/MW)/h]"] = pivot.get(("Automatic Frequency Restoration Reserve (aFRR)", "Down"))
    result["mFRR+ RZ [(EUR/MW)/h]"] = pivot.get(("Manual Frequency Restoration Reserve (mFRR)", "Up"))
    result["mFRR- RZ [(EUR/MW)/h]"] = pivot.get(("Manual Frequency Restoration Reserve (mFRR)", "Down"))
    result["FCR [EUR/MW]"] = fcr_avg
    result = result.reset_index().rename(columns={"Hour": "ISP(UTC)"})
    return result

def reshape_energy_data(df, mapcodes):
    # mapcodes can be a single code or a list
    if isinstance(mapcodes, str):
        codes = [mapcodes]
    else:
        codes = list(mapcodes)
    df = df[df["MapCode"].isin(codes)].copy()
    if df.empty:
        return pd.DataFrame()
    # Normalize reserve type labels to be resilient to minor naming changes
    df["ReserveType"] = df["ReserveType"].astype(str).str.strip()
    def _canon(rt: str) -> str:
        s = rt.lower()
        if "afrr" in s:
            return "Automatic Frequency Restoration Reserve (aFRR)"
        if "mfrr" in s:
            return "Manual Frequency Restoration Reserve (mFRR)"
        return rt
    df["ReserveType"] = df["ReserveType"].map(_canon)
    df["Hour"] = df["ISP(UTC)"].dt.floor("h")
    # Build robust up/down price using NotSpecified first, then fall back to Generation/Load
    df["UpPrice"] = df["NotSpecifiedUpPrice"].fillna(df["GenerationUpPrice"]).fillna(df["LoadUpPrice"]) if "GenerationUpPrice" in df.columns else df["NotSpecifiedUpPrice"].fillna(df.get("LoadUpPrice"))
    df["DownPrice"] = df["NotSpecifiedDownPrice"].fillna(df["GenerationDownPrice"]).fillna(df["LoadDownPrice"]) if "GenerationDownPrice" in df.columns else df["NotSpecifiedDownPrice"].fillna(df.get("LoadDownPrice"))
    df = df[["Hour", "ReserveType", "UpPrice", "DownPrice"]]
    df_up = df.pivot_table(
        index="Hour",
        columns="ReserveType",
        values="UpPrice",
        aggfunc="mean"
    )
    df_down = df.pivot_table(
        index="Hour",
        columns="ReserveType",
        values="DownPrice",
        aggfunc="mean"
    )
    df_combined = pd.DataFrame(index=df_up.index.union(df_down.index))
    df_combined["RE aFRR+ [EUR/MWh]"] = df_up.get("Automatic Frequency Restoration Reserve (aFRR)")
    df_combined["RE mFRR+ [EUR/MWh]"] = df_up.get("Manual Frequency Restoration Reserve (mFRR)")
    df_combined["RE aFRR- [EUR/MWh]"] = df_down.get("Automatic Frequency Restoration Reserve (aFRR)")
    df_combined["RE mFRR- [EUR/MWh]"] = df_down.get("Manual Frequency Restoration Reserve (mFRR)")
    df_combined = df_combined.reset_index().rename(columns={"Hour": "ISP(UTC)"})
    df_combined.fillna(0, inplace=True)
    return df_combined

def merge_tables(df_reserves, df_energy):
    if df_reserves.empty and not df_energy.empty:
        return df_energy.copy()
    if df_energy.empty and not df_reserves.empty:
        return df_reserves.copy()
    if df_reserves.empty and df_energy.empty:
        return pd.DataFrame()
    merged = pd.merge(df_reserves, df_energy, on="ISP(UTC)", how="outer", suffixes=('_RES', '_ENE'))
    merged = merged.sort_values("ISP(UTC)").reset_index(drop=True)
    return merged

def compute_daily_averages(df):
    df = df.copy()
    if "ISP(UTC)" not in df.columns:
        return pd.DataFrame()
    df["DATE"] = pd.to_datetime(df["ISP(UTC)"]).dt.date
    numeric_cols = [col for col in df.columns if col not in ["ISP(UTC)", "DATE"] and pd.api.types.is_numeric_dtype(df[col])]
    if not numeric_cols:
        return pd.DataFrame()
    daily_avg = df.groupby("DATE")[numeric_cols].mean().reset_index()
    daily_avg.rename(columns={"DATE": "Den"}, inplace=True)
    return daily_avg
