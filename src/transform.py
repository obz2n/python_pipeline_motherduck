import pandas as pd
from config import REQUIRED_COLUMNS


def transformar_dados(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpa valores monetários, localidades, dispositivos e datas.

    Retorna uma cópia para que o DataFrame da etapa de extração não seja
    alterado por efeitos colaterais.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df deve ser um pandas.DataFrame")

    missing_columns = REQUIRED_COLUMNS.difference(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Colunas obrigatórias ausentes: {missing}")

    transformed = df.copy()

    for column in ("Cost", "Sale_Amount"):
        raw_values = transformed[column].astype("string")
        cleaned_values = raw_values.str.replace(r"[^0-9.,-]", "", regex=True)
        cleaned_values = cleaned_values.str.replace(",", "", regex=False)
        transformed[column] = pd.to_numeric(cleaned_values, errors="coerce")
        invalid_values = raw_values.notna() & cleaned_values.ne("") & transformed[column].isna()
        if invalid_values.any():
            raise ValueError(f"Valores inválidos na coluna {column}")

    location_values = transformed["Location"].astype("string").str.strip().str.lower()

    campaign_name_values = transformed["Campaign_Name"].astype("string").str.strip().str.lower()
    campaign_name_values = campaign_name_values.str.replace("101", "", regex=False)
    campaign_name_values = campaign_name_values.str.replace("@", "a", regex=False)
    campaign_name_values = campaign_name_values.str.replace("3", "e", regex=False)
    campaign_name_values = campaign_name_values.str.replace("0", "o", regex=False)
    campaign_name_values = campaign_name_values.str.replace("1", "", regex=False)
    campaign_name_values = campaign_name_values.str.replace("_", "", regex=False)
    campaign_name_values = campaign_name_values.str.replace(r"[^a-z0-9\s]", "", regex=True)
    transformed["Campaign_Name"] = campaign_name_values.str.replace(r"\s+", " ", regex=True)

    ajustar = {
        "bengluru": "Bangalore",
        "benglore": "Bangalore",
        "bangalore": "Bangalore",
        "bengaluru": "Bangalore",
        "mumbay": "Mumbai",
        "mumabi": "Mumbai",
        "mumbai": "Mumbai",
        "bombay": "Mumbai",
        "dheli": "Delhi",
        "delhi": "Delhi",
        "newdlhi": "New Delhi",
        "new delhi": "New Delhi",
        "chnnai": "Chennai",
        "madras": "Chennai",
        "chenay": "Chennai",
        "chennai": "Chennai",
        "poona": "Pune",
        "punea": "Pune",
        "punr": "Pune",
        "pune": "Pune",
    }

    transformed["Location"] = location_values.replace(ajustar)
    transformed["Device"] = (
        transformed["Device"].astype("string").str.strip().str.lower().str.capitalize()
    )

    raw_dates = transformed["Ad_Date"].astype("string")
    transformed["Ad_Date"] = pd.to_datetime(
        raw_dates, format="mixed", dayfirst=True, errors="coerce"
    )
    invalid_dates = raw_dates.notna() & raw_dates.ne("") & transformed["Ad_Date"].isna()
    if invalid_dates.any():
        raise ValueError("Valores inválidos na coluna Ad_Date")
    return transformed
