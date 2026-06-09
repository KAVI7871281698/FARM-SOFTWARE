import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Officer

officers = Officer.objects.all()
count = 0
for officer in officers:
    if officer.group:
        officer.group_name = officer.group.name
        officer.save()
        count += 1

print(f"Successfully updated {count} officers.")
