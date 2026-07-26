import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Plot, NDVIRecord, Scout, ScoutAssignment, Officer

def sync_scouts():
    plots = Plot.objects.filter(ndvi_records__isnull=False).distinct()
    created_count = 0
    assigned_count = 0
    
    officers = list(Officer.objects.all())
    
    for plot in plots:
        latest = plot.ndvi_records.order_by('-date_recorded').first()
        if not latest:
            continue
            
        status_val = str(latest.health_status).strip()
        if status_val in ['Critical', 'Moderate', 'Need attention', 'Need Attention', 'moderate', 'critical', 'need attention']:
            active_scout = Scout.objects.filter(
                plot=plot,
                status__in=['Pending Assignment', 'Assigned']
            ).exists()
            
            if not active_scout:
                priority = 'High' if status_val in ['Critical', 'Need attention', 'Need Attention', 'critical', 'need attention'] else 'Medium'
                alert_reason = f"Automated Scout Alert: Plot Health Status dropped to {status_val}."
                
                scout = Scout.objects.create(
                    plot=plot,
                    ndvi_value=latest.ndvi_value,
                    alert_reason=alert_reason,
                    priority=priority,
                    status='Pending Assignment'
                )
                created_count += 1
                
                # Try to assign officer
                officer = None
                if plot.division_id:
                    div_id_str = str(plot.division_id)
                    for off in officers:
                        if off.division_ids:
                            cleaned = str(off.division_ids).replace('[', '').replace(']', '').replace("'", "").replace('"', "")
                            ids = [x.strip() for x in cleaned.split(',') if x.strip()]
                            if div_id_str in ids:
                                officer = off
                                break
                if officer:
                    ScoutAssignment.objects.create(
                        scout=scout,
                        officer=officer,
                        notes=f"Auto-assigned due to {status_val} health status."
                    )
                    scout.status = 'Assigned'
                    scout.save()
                    assigned_count += 1

    print(f"Sync complete! Created {created_count} scouts ({assigned_count} auto-assigned).")
    print(f"Total Scouts now: {Scout.objects.count()}")
    print(f"Pending: {Scout.objects.filter(status='Pending Assignment').count()}")
    print(f"Assigned: {Scout.objects.filter(status='Assigned').count()}")
    print(f"Critical Alerts (High): {Scout.objects.filter(priority='High').count()}")

if __name__ == '__main__':
    sync_scouts()
