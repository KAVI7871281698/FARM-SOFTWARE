import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Survey

surveys = Survey.objects.filter(group_id__isnull=True)
count = surveys.count()
print(f"Total surveys missing group_id: {count}")

updated = 0
for idx, survey in enumerate(surveys):
    survey.save()
    updated += 1
    if idx % 100 == 0:
        print(f"Updated {idx} surveys...")
        
print(f"Total updated: {updated}")

surveys_after = Survey.objects.filter(group_id__isnull=True).count()
print(f"Remaining surveys missing group_id: {surveys_after}")
