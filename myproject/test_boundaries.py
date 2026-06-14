import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from myapp.models import Plot

plot = Plot.objects.filter(id=6).first()
if plot:
    print("Plot before:", plot.boundaries)
    plot.boundaries = [{"point1": 11.0168, "pont2": 76.955899}]
    plot.save()
    print("Plot memory after save:", plot.boundaries)
    
    plot.refresh_from_db()
    print("Plot DB after save:", plot.boundaries)
else:
    print("Plot not found")
