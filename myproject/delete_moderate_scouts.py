import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Scout

# Find and delete any scouts that were created for Moderate health status
scouts_to_delete = Scout.objects.filter(alert_reason__icontains='Moderate')
count = scouts_to_delete.count()
scouts_to_delete.delete()
print(f"Deleted {count} scouts that were created for Moderate plots.")
