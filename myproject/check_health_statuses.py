import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import NDVIRecord

print(NDVIRecord.objects.values_list('health_status', flat=True).distinct())
