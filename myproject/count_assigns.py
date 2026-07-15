import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import WorkAssign, Officer

print("Total WorkAssign objects:", WorkAssign.objects.count())
