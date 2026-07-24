import os
import django
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Plot, Survey, SurveyResult, Officer, STAGE_SURVEY_DAYS

plots = Plot.objects.exclude(planting_date__isnull=True).prefetch_related('group', 'factory')
officers = list(Officer.objects.all())

print(f"Total plots to process: {plots.count()}")
created_count = 0

for idx, plot in enumerate(plots):
    officer = None
    if plot.division_id:
        div_id_str = str(plot.division_id)
        for off in officers:
            if off.division_ids:
                cleaned = off.division_ids.replace('[', '').replace(']', '').replace("'", "").replace('"', "")
                ids = [x.strip() for x in cleaned.split(',') if x.strip()]
                if div_id_str in ids:
                    officer = off
                    break

    for stage, survey_days in STAGE_SURVEY_DAYS.items():
        if not survey_days:
            continue
            
        survey_exists = Survey.objects.filter(plot=plot, survey_stage=stage).exists()
        if not survey_exists:
            allocated_dates = []
            base_date = plot.planting_date
            
            for day_offset in survey_days:
                calc_date = base_date + datetime.timedelta(days=day_offset)
                allocated_dates.append(calc_date.strftime('%Y-%m-%d'))
                
            number_of_days = len(allocated_dates)
            first_date_obj = base_date + datetime.timedelta(days=survey_days[0])
            survey_month = first_date_obj.strftime('%B %Y')
            
            survey = Survey.objects.create(
                plot=plot,
                officer=officer,
                survey_stage=stage,
                title=f"{stage} Survey for Plot {plot.plot_code}",
                description=f"Auto-assigned future survey for {stage} stage based on planting date.",
                number_of_days=number_of_days,
                allocated_dates=allocated_dates,
                survey_month=survey_month
            )
            
            for date_str in allocated_dates:
                survey_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                SurveyResult.objects.create(
                    survey=survey,
                    survey_date=survey_date,
                    survey_status='Pending'
                )
            created_count += 1
            print(f"Created {stage} Survey for Plot {plot.plot_code}")
            
    if idx % 10 == 0:
        print(f"Processed {idx} plots...")

print(f"Total missing future surveys created: {created_count}")
