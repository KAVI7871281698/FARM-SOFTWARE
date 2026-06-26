import os

path = r'd:\Own Apps\Clients docs\Farm Signals\myproject\myapp\views.py'
with open(path, 'a', encoding='utf-8') as f:
    f.write('''

# ==========================================
# NDVI Monitoring & Scout Management
# ==========================================

from .models import NDVIRecord, Scout, ScoutAssignment, ScoutSurveyReport

def ndvi_dashboard(request):
    # This view will show the plot-wise NDVI and historical trends
    # In a real app, this would query Sentinel-2 APIs. We'll show existing NDVIRecords.
    plots = Plot.objects.filter(ndvi_records__isnull=False).distinct()
    
    # Let's get the latest NDVI record for each plot to show on the map
    plot_data = []
    for plot in plots:
        latest = plot.ndvi_records.order_by('-date_recorded').first()
        if latest and plot.center_lt_ln:
            plot_data.append({
                'plot_code': plot.plot_code,
                'farmer': plot.farmer.name if plot.farmer else '',
                'lat': plot.center_lt_ln.get('lat', 0) if isinstance(plot.center_lt_ln, dict) else plot.latitude,
                'lng': plot.center_lt_ln.get('lng', 0) if isinstance(plot.center_lt_ln, dict) else plot.longitude,
                'ndvi_value': str(latest.ndvi_value),
                'health_status': latest.health_status,
                'date': str(latest.date_recorded)
            })

    context = {
        'plots': plots,
        'plot_data_json': json.dumps(plot_data)
    }
    return render(request, 'ndvi_dashboard.html', context)

def scout_management(request):
    scouts = Scout.objects.all().order_by('-created_at')
    officers = Officer.objects.all()
    
    total_scouts = scouts.count()
    pending_scouts = scouts.filter(status='Pending Assignment').count()
    assigned_scouts = scouts.filter(status='Assigned').count()
    completed_scouts = scouts.filter(status='Completed').count()
    critical_alerts = scouts.filter(priority='High').count()

    context = {
        'scouts': scouts,
        'officers': officers,
        'total_scouts': total_scouts,
        'pending_scouts': pending_scouts,
        'assigned_scouts': assigned_scouts,
        'completed_scouts': completed_scouts,
        'critical_alerts': critical_alerts,
    }
    return render(request, 'scout_management.html', context)

def assign_scout(request):
    if request.method == 'POST':
        scout_id = request.POST.get('scout_id')
        officer_id = request.POST.get('officer_id')
        notes = request.POST.get('notes', '')

        try:
            scout = Scout.objects.get(id=scout_id)
            officer = Officer.objects.get(id=officer_id)
            
            # Create or update assignment
            assignment, created = ScoutAssignment.objects.update_or_create(
                scout=scout,
                defaults={'officer': officer, 'notes': notes}
            )
            
            # Update Scout status
            scout.status = 'Assigned'
            scout.save()
            
            messages.success(request, f'Scout {scout.scout_id} assigned to {officer.name}.')
        except Exception as e:
            messages.error(request, f'Error assigning scout: {str(e)}')
            
    return redirect('scout_management')

def generate_mock_ndvi(request):
    """
    Endpoint to trigger mock NDVI generation and Scout alerts.
    Simulates checking Sentinel-2.
    """
    import random
    from datetime import date
    
    plots = Plot.objects.all()[:10] # just process a few for testing
    count = 0
    alerts = 0
    for plot in plots:
        val = random.uniform(0.3, 0.9)
        status = 'Healthy'
        priority = 'Low'
        
        if val < 0.4:
            status = 'Critical'
            priority = 'High'
        elif val < 0.6:
            status = 'Moderate'
            priority = 'Medium'
            
        NDVIRecord.objects.create(
            plot=plot,
            date_recorded=date.today(),
            ndvi_value=val,
            health_status=status
        )
        count += 1
        
        # Trigger scout creation if critical
        if status == 'Critical':
            Scout.objects.create(
                plot=plot,
                ndvi_value=val,
                alert_reason='NDVI dropped below critical threshold (0.4)',
                priority=priority,
                status='Pending Assignment'
            )
            alerts += 1
            
    messages.success(request, f'Generated {count} NDVI records and {alerts} Scout Alerts.')
    return redirect('ndvi_dashboard')

''')
