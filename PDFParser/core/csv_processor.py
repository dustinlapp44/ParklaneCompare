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

    


def tradify_grouping(df: pd.DataFrame, job_col: str = "Job No", amount_col: str = "Hours") -> pd.DataFrame:
    result_parts = []

    for job_id, group in df.groupby(job_col, sort=False):
        # Append the group rows
        result_parts.append(group)

        # Create subtotal row
        subtotal_row = {col: "" for col in df.columns}
        subtotal_row[job_col] = ""  # Keep job_id blank for total rows
        subtotal_row[amount_col] = group[amount_col].sum()

        # Append subtotal as DataFrame
        result_parts.append(pd.DataFrame([subtotal_row], columns=df.columns))

    # Concatenate back into one DataFrame
    result_df = pd.concat(result_parts, ignore_index=True)

    return result_df

# 🔧 Formatter functions

def generate_hourly(df: pd.DataFrame, hourly_rate: float = 62) -> pd.DataFrame:
    ## Add check for hours being in float form already
    if df['Hours'].dtype == str:
        df['Hours'] = df['Hours'].apply(convert_hours_to_float)
    new_amount = df['Hours'] * hourly_rate
    hours_index = df.columns.get_loc('Hours')
    df.insert(hours_index + 1, 'Amount', new_amount)
    return df

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