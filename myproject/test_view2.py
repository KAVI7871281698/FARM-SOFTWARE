import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from myapp.views import filter_by_factory
from myapp.models import Plot
from django.db.models import Q
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware

factory = RequestFactory()
request = factory.get('/')
middleware = SessionMiddleware(lambda r: None)
middleware.process_request(request)
request.session['role_id'] = '2'
request.session['factory_ids'] = '1'
request.session.save()

base_plots = Plot.objects.filter(
    Q(center_lt_ln__isnull=False) | 
    (Q(latitude__isnull=False) & Q(longitude__isnull=False))
)
plots = filter_by_factory(base_plots, 'farmer__section__division__factory_name_id', request)

plots_data = []
for p in plots:
    try:
        lat, lon = None, None
        
        # First try center_lt_ln
        if p.center_lt_ln:
            if isinstance(p.center_lt_ln, list) and len(p.center_lt_ln) >= 2:
                lat = float(p.center_lt_ln[0])
                lon = float(p.center_lt_ln[1])
        
        # Fallback to latitude/longitude fields
        if lat is None or lon is None:
            lat_str = str(p.latitude).strip("[]'\"")
            lon_str = str(p.longitude).strip("[]'\"")
            if lat_str and lon_str and lat_str != 'None' and lon_str != 'None':
                lat = float(lat_str)
                lon = float(lon_str)
        
        if lat is None or lon is None:
            continue
            
        plots_data.append({
            'id': p.id,
            'plot_code': p.plot_code or 'Unknown',
            'lat': lat,
            'lon': lon,
            'division': p.division_name or (p.division.name if p.division else '-'),
            'section': p.section_name or (p.section.section_name if p.section else '-'),
            'village': p.village_name or (p.village.village_name if p.village else '-'),
            'farmer_name': p.farmer.name if p.farmer else '-',
            'planting_date': str(p.planting_date) if p.planting_date else '-',
            'acres': str(p.area_acre) if p.area_acre else '-',
            'soil_type': p.soil_type.soil_name if p.soil_type else '-',
            'status': p.status or '-'
        })
    except (ValueError, TypeError, IndexError) as e:
        print("EXCEPTION CAUGHT:", p.id, type(e), e)
        continue

import json
print("PLOTS_DATA:", json.dumps(plots_data))
