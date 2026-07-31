import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Plot, Officer

plots = Plot.objects.filter(officer__isnull=True).exclude(division_name__isnull=True)
updated_count = 0
not_found_count = 0

for plot in plots:
    div_name = plot.division_name
    # Find an officer who has this division in their division_names
    assigned = False
    for off in Officer.objects.exclude(division_names__isnull=True).exclude(division_names=''):
        d_names = [d.strip() for d in str(off.division_names).split(',')]
        if div_name in d_names:
            plot.officer = off
            plot.save(update_fields=['officer'])
            updated_count += 1
            assigned = True
            break
            
    if not assigned:
        not_found_count += 1

print(f"Updated {updated_count} plots. {not_found_count} plots still have no matching officer for their division.")
