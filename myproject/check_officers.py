import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Plot
print("Total plots:", Plot.objects.count())
print("Null officers:", Plot.objects.filter(officer__isnull=True).count())
print("Null officers with section:", Plot.objects.filter(officer__isnull=True, section__isnull=False).count())
