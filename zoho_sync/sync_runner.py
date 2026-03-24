from dotenv import load_dotenv
load_dotenv()

from zoho_sync.sync_service import run_sync

def main():
    run_sync()

if __name__ == "__main__":
    main()