import pandas as pd


class CSVExporter:
    @staticmethod
    def export(dataframe: pd.DataFrame, path: str):
        dataframe.to_csv(path, index=False)
