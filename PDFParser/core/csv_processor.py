import pandas as pd


class CSVProcessor:
    def __init__(self, csv_path, formatters=None):
        self.csv_path = csv_path
        self.formatters = formatters or []

    def load_and_process(self) -> pd.DataFrame:
        df = pd.read_csv(self.csv_path)

        for func in self.formatters:
            df = func(df)

        return df

    

# 🔧 Formatter functions

def strip_whitespace(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [col.strip() for col in df.columns]
    return df.applymap(lambda x: x.strip() if isinstance(x, str) else x)


def convert_hours_to_float(df: pd.DataFrame) -> pd.DataFrame:
    def time_to_float(t):
        if isinstance(t, str) and ':' in t:
            h, m = t.split(':')
            return round(int(h) + int(m)/60.0, 2)
        return t

    for col in df.columns:
        if df[col].astype(str).str.match(r"^\d{1,2}:\d{2}$").any():
            df[col] = df[col].apply(time_to_float)

    return df