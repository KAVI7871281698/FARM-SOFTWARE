import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Village

count = 0
for v in Village.objects.all():
    if not v.division and v.section and v.section.division:
        v.division = v.section.division.name
        v.save()
        count += 1
print(f'Updated {count} villages.')
