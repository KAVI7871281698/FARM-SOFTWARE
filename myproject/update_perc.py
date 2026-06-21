import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Survey, SurveyResult

updated = 0
for survey in Survey.objects.all():
    allocated_count = survey.number_of_days
    if allocated_count and allocated_count > 0:
        completed_count = survey.results.filter(status='Completed').values('survey_date').distinct().count()
        perc = min(int((completed_count / allocated_count) * 100), 100)
    else:
        perc = 100
    
    SurveyResult.objects.filter(survey=survey).update(completion_percentage=perc)
    updated += 1

print(f'Updated {updated} surveys')
