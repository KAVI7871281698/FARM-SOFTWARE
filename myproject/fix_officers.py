import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Plot, Officer

plots = Plot.objects.filter(officer__isnull=True).exclude(section__isnull=True)
updated_count = 0

for plot in plots:
    for off in Officer.objects.exclude(section_ids__isnull=True).exclude(section_ids=''):
        s_ids = [s.strip() for s in str(off.section_ids).split(',')]
        if str(plot.section_id) in s_ids:
            plot.officer = off
            plot.save(update_fields=['officer'])
            updated_count += 1
            break

print(f"Updated {updated_count} plots with their corresponding officers.")
