import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Officer

count = 0
officers = Officer.objects.filter(role__isnull=False, role_name__isnull=True)
for o in officers:
    o.role_name = o.role.name
    o.save(update_fields=['role_name'])
    count += 1
print(f'Updated {count} officers')
