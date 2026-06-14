import os
import django
from django.test import RequestFactory

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from myapp.views import api_add_plot
from myapp.models import Plot, Farmer

# Set up test data
farmer = Farmer.objects.first()
plot = Plot.objects.filter(id=5).first()
if not plot:
    print("Plot 5 not found!")
else:
    # First, let's artificially set the DB state to the "old" boundaries
    plot.boundaries = [{"point1": 11.0168, "point2": 76.9558}]
    plot.save()
    print("DB state before API call:", plot.boundaries)
    
    # Now simulate the mobile app's API call with the NEW boundaries
    factory = RequestFactory()
    data = {
        "plot_id": 5,
        "officer_id": plot.officer.id if plot.officer else 22,
        "farmer_name": plot.farmer.id if plot.farmer else 4,
        "boundaries": '[{"point1": 11.0168, "pont2": 76.955899}]'
    }
    
    request = factory.post('/api/add_plot/', data=data)
    response = api_add_plot(request)
    
    import json
    res_data = json.loads(response.content.decode('utf-8'))
    print("API Response boundaries:", res_data.get('data', {}).get('boundaries'))
    print("API Response debug_extracted:", res_data.get('data', {}).get('debug_extracted'))
