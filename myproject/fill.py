import os
import django
from datetime import timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from myapp.models import Plot

plots = Plot.objects.filter(harvest_date__isnull=True)
count = 0
updates = []
for p in plots:
    if p.planting_date:
        p.harvest_date = p.planting_date + timedelta(days=365)
        updates.append(p)
        count += 1

Plot.objects.bulk_update(updates, ['harvest_date'])
print(f"Updated {count} plots with calculated harvest date (+365 days).")
