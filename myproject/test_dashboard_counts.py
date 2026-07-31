import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Plot, NDVIRecord, Scout

plots_qs = Plot.objects.all()

mapped_plot_ids = set(plots_qs.filter(status__in=['Mapped', 'mapped'] ).values_list('id', flat=True)) | set(plots_qs.filter(boundaries__isnull=False).exclude(boundaries='').values_list('id', flat=True))

latest_ndvis = NDVIRecord.objects.filter(plot__in=plots_qs).order_by('plot', '-date_recorded').distinct('plot')
ndvi_dict = {n.plot_id: n for n in latest_ndvis}

health_counts = {'Healthy': 0, 'Moderate': 0, 'Critical': 0}
for p_id in mapped_plot_ids:
    health_status = 'Healthy'
    latest_ndvi = ndvi_dict.get(p_id)
    if latest_ndvi:
        ndvi_h = latest_ndvi.health_status
        if ndvi_h == 'Good':
            health_status = 'Healthy'
        elif ndvi_h == 'Moderate':
            health_status = 'Moderate'
        elif ndvi_h in ['Need Attention', 'Critical', 'Need attention', 'critical', 'need attention']:
            health_status = 'Critical'
    health_counts[health_status] += 1

print("Dashboard Health Counts:", health_counts)

scout_pending = Scout.objects.filter(plot__in=plots_qs, status='Pending Assignment').count()
scout_assigned = Scout.objects.filter(plot__in=plots_qs, status='Assigned').count()
print("Pending Scouts:", scout_pending, "Assigned Scouts:", scout_assigned)
