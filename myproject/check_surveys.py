import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Factory

for f in Factory.objects.all():
    print(f"Factory: id={f.id} code={f.code} name={f.name}")
