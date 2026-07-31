import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Scout, Plot

active_scouts = Scout.objects.filter(status__in=['Pending Assignment', 'Assigned'])
print(f"Total active scouts: {active_scouts.count()}")

currently_critical = 0
for s in active_scouts:
    latest_ndvi = s.plot.ndvi_records.order_by('-date_recorded').first()
    if latest_ndvi and latest_ndvi.health_status in ['Critical', 'Need attention', 'Need Attention', 'critical', 'need attention']:
        currently_critical += 1

print(f"Active scouts on plots that are CURRENTLY critical: {currently_critical}")
