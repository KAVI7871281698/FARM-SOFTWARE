import os
import django
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Survey, SurveyResult, STAGE_SURVEY_DAYS, NDVIRecord

surveys_to_fix = Survey.objects.filter(allocated_dates__isnull=True)
fixed_count = 0

for survey in surveys_to_fix:
    survey_days = STAGE_SURVEY_DAYS.get(survey.survey_stage, [])
    
    if survey_days:
        # Try to find the corresponding NDVIRecord that triggered this
        ndvi = NDVIRecord.objects.filter(plot=survey.plot, stage=survey.survey_stage).order_by('date_recorded').first()
        if ndvi and ndvi.date_recorded:
            base_date = ndvi.date_recorded
        else:
            base_date = survey.created_at.date()
            
        first_day_offset = survey_days[0]
        allocated_dates = []
        
        for day_offset in survey_days:
            relative_offset = day_offset - first_day_offset
            calc_date = base_date + datetime.timedelta(days=relative_offset)
            allocated_dates.append(calc_date.strftime('%Y-%m-%d'))
            
        survey.number_of_days = len(allocated_dates)
        survey.allocated_dates = allocated_dates
        survey.survey_month = base_date.strftime('%B %Y')
        survey.save()
        
        # Create SurveyResult if they don't exist
        for date_str in allocated_dates:
            survey_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            SurveyResult.objects.get_or_create(
                survey=survey,
                survey_date=survey_date,
                defaults={'survey_status': 'Pending'}
            )
        fixed_count += 1
        print(f"Fixed Survey ID {survey.id}: month={survey.survey_month}, days={survey.number_of_days}, dates={allocated_dates}")

print(f"Total fixed: {fixed_count}")
