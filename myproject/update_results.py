import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import SurveyResult

results = SurveyResult.objects.filter(status='Pending')
updated = 0
for r in results:
    if r.weed_infestation or r.tillering_vigour or r.remarks or r.field_photo1:
        r.status = 'Completed'
        r.save()
        updated += 1

print(f'Updated {updated} records')
