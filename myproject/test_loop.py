import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from myapp.models import Plot

plots = Plot.objects.filter(id__in=[5,6,7])
for p in plots:
    try:
        plots_data = []
        lat = p.center_lt_ln[0]
        lon = p.center_lt_ln[1]
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
        print('SUCCESS', p.id)
    except Exception as e:
        print('ERROR', p.id, type(e), e)
