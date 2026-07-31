import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Officer

print("Officers with section_names:")
for off in Officer.objects.exclude(section_names__isnull=True).exclude(section_names=''):
    print(off.name, off.section_names)

print("\nOfficers with division_names:")
for off in Officer.objects.exclude(division_names__isnull=True).exclude(division_names=''):
    print(off.name, off.division_names)
