import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Officer, Plot

print("Officers section_ids:")
for off in Officer.objects.all():
    print(off.id, off.name, off.section_ids)

print("\nSample Plot section_ids:")
for p in Plot.objects.filter(section__isnull=False)[:5]:
    print(p.id, p.plot_code, p.section_id)
