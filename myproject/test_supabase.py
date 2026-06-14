import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
if url and url.endswith('/rest/v1/'):
    url = url[:-9]
key: str = os.environ.get("SUPABASE_KEY")

print(f"URL: {url}")
supabase: Client = create_client(url, key)

file_content = b"fake image content"
file_name = "test_upload.txt"
content_type = "text/plain"

try:
    res = supabase.storage.from_('plot_boundaries').upload(
        file=file_content,
        path=file_name,
        file_options={"content-type": content_type}
    )
    print("Upload result:", res)
    public_url = supabase.storage.from_('plot_boundaries').get_public_url(file_name)
    print("Public URL:", public_url)
    
    # Clean up
    supabase.storage.from_('plot_boundaries').remove([file_name])
except Exception as e:
    print("Error:", e)
