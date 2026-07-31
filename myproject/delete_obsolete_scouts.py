import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Scout, Plot

active_scouts = Scout.objects.filter(status__in=['Pending Assignment', 'Assigned'])
deleted_count = 0

for s in active_scouts:
    latest_ndvi = s.plot.ndvi_records.order_by('-date_recorded').first()
    is_currently_critical = False
    
    if latest_ndvi:
        status_val = str(latest_ndvi.health_status).strip()
        if status_val in ['Critical', 'Need attention', 'Need Attention', 'critical', 'need attention']:
            is_currently_critical = True
            
    if not is_currently_critical:
        # Plot is no longer critical, so we can delete this obsolete scout alert
        s.delete()
        deleted_count += 1

print(f"Deleted {deleted_count} obsolete scouts. Plots are no longer Critical.")
