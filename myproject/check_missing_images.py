import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Plot
from django.conf import settings

media_dir = os.path.join(settings.BASE_DIR, 'media')

plots = Plot.objects.all()
missing = 0
found = 0

missing_codes = []

for p in plots:
    img_path = os.path.join(media_dir, f"{p.plot_code}.png")
    if os.path.exists(img_path):
        found += 1
    else:
        missing += 1
        missing_codes.append(p.plot_code)

print(f"Plots with image: {found}")
print(f"Plots missing image: {missing}")
if missing_codes:
    print(f"Sample missing codes: {missing_codes[:10]}")
