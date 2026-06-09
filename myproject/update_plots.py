import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Plot

plots = Plot.objects.filter(farmer__isnull=False)
updated_count = 0
for plot in plots:
    if not plot.group and plot.farmer.group:
        plot.group = plot.farmer.group
        plot.group_name = plot.farmer.group_name
        plot.factory = plot.farmer.factory
        plot.factory_name = plot.farmer.factory_name
        plot.save()
        updated_count += 1

print(f"Successfully updated {updated_count} existing plots!")
