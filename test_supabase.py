from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client

sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

docs = sb.table('documents').select('id', count='exact').execute()
sync = sb.table('sync_log').select('*').execute()

print('Vectors indexed so far:', docs.count)
print('Files synced so far:', len(sync.data))

if sync.data:
    for row in sync.data:
        print(f"  - {row['file_name']} ({row['chunks']} chunks)")
else:
    print('No files synced yet')