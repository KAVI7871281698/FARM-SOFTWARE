import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Scout

active_scouts = Scout.objects.filter(status__in=['Pending Assignment', 'Assigned'])
mapped_critical = 0
unmapped_critical = 0

for s in active_scouts:
    latest_ndvi = s.plot.ndvi_records.order_by('-date_recorded').first()
    if latest_ndvi and latest_ndvi.health_status in ['Critical', 'Need attention', 'Need Attention', 'critical', 'need attention']:
        if s.plot.status in ['Mapped', 'mapped'] or bool(s.plot.boundaries):
            mapped_critical += 1
        else:
            unmapped_critical += 1

print(f"Mapped Critical plots with active scouts: {mapped_critical}")
print(f"Unmapped Critical plots with active scouts: {unmapped_critical}")
