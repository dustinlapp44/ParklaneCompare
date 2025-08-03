from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import os

class GoogleDriveClient:
    def __init__(self, credentials_file='client_secrets.json'):
        """
        Initializes the Google Drive client with OAuth2 authentication.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.credentials_path = os.path.join(base_dir, credentials_file)

        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(f"Credentials file not found: {self.credentials_path}")
        
        self.gauth = GoogleAuth()
        self.gauth.LoadClientConfigFile(self.credentials_path)

        # Ensure offline access for refresh token
        self.gauth.GetFlow()
        self.gauth.flow.params.update({'access_type': 'offline'})

        # Load existing token if available
        self.token_path = os.path.join(base_dir, 'token.json')
        self.gauth.LoadCredentialsFile(self.token_path)
        if self.gauth.credentials is None:
            self.gauth.LocalWebserverAuth()
        elif self.gauth.access_token_expired:
            self.gauth.Refresh()
        else:
            self.gauth.Authorize()

        self.gauth.SaveCredentialsFile(self.token_path)
        self.drive = GoogleDrive(self.gauth)

    def upload_file(self, local_path, remote_name=None, parent_folder_id=None, overwrite=True):
        """
        Uploads a file to Google Drive, optionally overwriting an existing file with the same name in the target folder.

        :param local_path: Path to the local file
        :param remote_name: Name for the file in Drive (defaults to local file name)
        :param parent_folder_id: Optional Drive folder ID to upload into
        :param overwrite: If True, overwrite existing file with same name
        :return: File ID of the uploaded file
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")

        remote_name = remote_name or os.path.basename(local_path)

        # Check for existing file if overwrite enabled
        existing_file_id = None
        if overwrite:
            query = f"title='{remote_name}' and trashed=false"
            if parent_folder_id:
                query += f" and '{parent_folder_id}' in parents"
            existing_files = self.drive.ListFile({'q': query}).GetList()
            if existing_files:
                existing_file_id = existing_files[0]['id']

        # Create or update file
        if existing_file_id:
            gfile = self.drive.CreateFile({'id': existing_file_id})
        else:
            file_metadata = {'title': remote_name}
            if parent_folder_id:
                file_metadata['parents'] = [{'id': parent_folder_id}]
            gfile = self.drive.CreateFile(file_metadata)

        gfile.SetContentFile(local_path)
        gfile.Upload()

        action = "Updated" if existing_file_id else "Uploaded"
        print(f"{action} {remote_name} (ID: {gfile['id']})")
        return gfile['id']

    def download_file(self, file_id, local_path):
        gfile = self.drive.CreateFile({'id': file_id})
        gfile.GetContentFile(local_path)
        print(f"Downloaded file to {local_path}")

    def list_files(self, query=""):
        file_list = self.drive.ListFile({'q': query}).GetList()
        return file_list

    def get_full_path(self, file):
        """
        Recursively builds the full path for a file.
        """
        path_parts = [file['title']]
        parent_ids = file.get('parents', [])

        while parent_ids:
            parent_id = parent_ids[0]['id']
            if parent_id == 'root':
                path_parts.insert(0, 'My Drive')
                break
            parent = self.drive.CreateFile({'id': parent_id})
            parent.FetchMetadata(fields='title,parents')
            path_parts.insert(0, parent['title'])
            parent_ids = parent.get('parents', [])

        return '/'.join(path_parts)

    def list_files_with_paths(self, query=""):
        """
        Lists files matching a query with their full folder paths.
        """
        results = []
        file_list = self.drive.ListFile({'q': query}).GetList()
        for file in file_list:
            full_path = self.get_full_path(file)
            results.append({
                'id': file['id'],
                'title': file['title'],
                'path': full_path
            })
        return results

    def upload_file_to_folder_path(self, local_path, folder_path):
        """
        Uploads a file to Google Drive into the specified folder path, creating folders if needed.

        :param local_path: Path to the local file
        :param folder_path: Folder path in Drive, e.g. 'My Drive/Invoices/July'
        :return: File ID of the uploaded file
        """
        folder_id = self.get_or_create_folder_by_path(folder_path)
        return self.upload_file(local_path, parent_folder_id=folder_id)

    def get_or_create_folder_by_path(self, folder_path):
        """
        Traverses Drive to find a folder by path, creating folders if missing.

        :param folder_path: Folder path, e.g. 'My Drive/Invoices/July'
        :return: The folder ID
        """
        parts = folder_path.strip('/').split('/')
        parent_id = 'root'
        for part in parts:
            # Search for folder with this name under parent_id
            query = f"'{parent_id}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder' and title='{part}'"
            folder_list = self.drive.ListFile({'q': query}).GetList()
            if folder_list:
                folder = folder_list[0]
            else:
                # Create folder if not found
                folder_metadata = {
                    'title': part,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [{'id': parent_id}]
                }
                folder = self.drive.CreateFile(folder_metadata)
                folder.Upload()
            parent_id = folder['id']
        return parent_id
    
if __name__ == "__main__":
    # Example usage
    client = GoogleDriveClient()
    client.upload_file('example.txt', remote_name='UploadedExample.txt')
    print(client.list_files_with_paths("title contains 'UploadedExample'"))
    client.download_file('your_file_id_here', 'downloaded_example.txt')
    print("Done.")