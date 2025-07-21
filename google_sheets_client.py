import gspread
from google.oauth2.service_account import Credentials

class GoogleSheetsClient:
    def __init__(self, credentials_path='service_account.json'):
        """
        Initializes Google Sheets client using Service Account credentials.
        """
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
        self.credentials = Credentials.from_service_account_file(
            credentials_path, scopes=scopes)
        self.client = gspread.authorize(self.credentials)

    def read_sheet_as_lists(self, sheet_url_or_key, worksheet_name=None):
        """
        Reads a Google Sheet and returns data as a list of rows.

        :param sheet_url_or_key: The full URL or key of the Google Sheet
        :param worksheet_name: Optional specific worksheet to read
        :return: List of rows, each row is a list of cell values
        """
        sheet = self.client.open_by_url(sheet_url_or_key) if sheet_url_or_key.startswith('http') \
            else self.client.open_by_key(sheet_url_or_key)

        worksheet = sheet.worksheet(worksheet_name) if worksheet_name else sheet.sheet1
        data = worksheet.get_all_values()
        return data

    def read_sheet_as_dataframe(self, sheet_url_or_key, worksheet_name=None):
        """
        Reads a Google Sheet into a pandas DataFrame.

        :param sheet_url_or_key: The full URL or key of the Google Sheet
        :param worksheet_name: Optional specific worksheet to read
        :return: pandas DataFrame of the sheet data
        """
        import pandas as pd
        data = self.read_sheet_as_lists(sheet_url_or_key, worksheet_name)
        df = pd.DataFrame(data[1:], columns=data[0])  # first row as header
        return df
