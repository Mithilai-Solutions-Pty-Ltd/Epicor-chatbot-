from dotenv import load_dotenv
load_dotenv()
import os, requests

resp = requests.post(os.environ['ZOHO_ACCOUNTS_URL'], data={
    'grant_type': 'refresh_token',
    'client_id': os.environ['ZOHO_CLIENT_ID'],
    'client_secret': os.environ['ZOHO_CLIENT_SECRET'],
    'refresh_token': os.environ['ZOHO_REFRESH_TOKEN'],
})
token = resp.json()['access_token']

base = os.environ['ZOHO_WORKDRIVE_URL']
folder_id = os.environ['ZOHO_TEAM_FOLDER_ID']
headers = {
    'Authorization': f'Zoho-oauthtoken {token}',
    'Accept': 'application/vnd.api+json'
}

# Get team folder name
r = requests.get(f'{base}/teamfolders/{folder_id}', headers=headers)
attrs = r.json().get('data', {}).get('attributes', {})
print('Team Folder Name:', attrs.get('name'))
print('Team Folder ID:', folder_id)

# Get subfolders
r2 = requests.get(
    f'{base}/teamfolders/{folder_id}/files',
    headers=headers,
    params={'page[limit]': 50}
)
items = r2.json().get('data', [])
print('\nSubfolders and files:')
for item in items:
    a = item.get('attributes', {})
    name = a.get('name')
    item_id = item.get('id')
    item_type = a.get('type', 'file')
    icon = '📁' if item_type == 'folder' else '📄'
    print(f'  {icon} {name} — ID: {item_id}')