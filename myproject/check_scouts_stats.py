import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Scout, NDVIRecord, Plot

print("Total Scouts:", Scout.objects.count())
print("Completed Scouts:", Scout.objects.filter(status='Completed').count())
print("Pending/Assigned:", Scout.objects.filter(status__in=['Pending Assignment', 'Assigned']).count())

# Let's see how many active scouts are on unmapped plots
unmapped_active_scouts = 0
for s in Scout.objects.filter(status__in=['Pending Assignment', 'Assigned']):
    if s.plot.status not in ['Mapped', 'mapped'] and not s.plot.boundaries:
        unmapped_active_scouts += 1

print("Active Scouts on Unmapped Plots:", unmapped_active_scouts)
