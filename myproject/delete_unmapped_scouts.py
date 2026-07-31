import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Scout

active_scouts = Scout.objects.filter(status__in=['Pending Assignment', 'Assigned'])
unmapped_count = 0

for s in active_scouts:
    is_mapped = s.plot.status in ['Mapped', 'mapped'] or bool(s.plot.boundaries)
    if not is_mapped:
        unmapped_count += 1
        s.delete()

print(f"Deleted {unmapped_count} active scouts that were on UNMAPPED plots.")
