import os
import django
from datetime import datetime, timedelta
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Plot, NDVIRecord
from django.utils import timezone

def get_stage_for_days(days):
    if days <= 30:
        return 'Germination'
    elif days <= 75:
        return 'Early Tiller'
    elif days <= 120:
        return 'Tillering'
    elif days <= 240:
        return 'Grand growth'
    else:
        return 'Maturity'

def get_ndvi_range_for_stage(stage):
    ranges = {
        'Germination': (0.2, 0.4),
        'Early Tiller': (0.35, 0.6),
        'Tillering': (0.55, 0.7),
        'Grand growth': (0.65, 0.8),
        'Maturity': (0.6, 0.7)
    }
    return ranges.get(stage, (0.2, 0.8))

print("Deleting existing NDVI records to prevent duplicates...")
NDVIRecord.objects.all().delete()

plots = Plot.objects.all()
if not plots.exists():
    print("No plots found in the database. Please add plots first.")
    exit()

print(f"Generating NDVI records for {plots.count()} plots...")
today = timezone.now().date()

for plot in plots:
    # Use planting date or default to 180 days ago
    planting_date = plot.planting_date if plot.planting_date else today - timedelta(days=180)
    
    # Generate a reading every 15 days from planting date up to today
    current_date = planting_date
    while current_date <= today:
        days_since_planting = (current_date - planting_date).days
        stage = get_stage_for_days(days_since_planting)
        min_val, max_val = get_ndvi_range_for_stage(stage)
        
        ndvi_mean = round(random.uniform(min_val, max_val), 4)
        ndvi_min = max(0.1, ndvi_mean - round(random.uniform(0.05, 0.15), 4))
        ndvi_max = min(1.0, ndvi_mean + round(random.uniform(0.05, 0.15), 4))
        
        thr_min = min_val
        thr_max = max_val
        
        # Determine health status based on mean vs thresholds
        if ndvi_mean >= min_val and ndvi_mean <= max_val:
            health = 'Good'
            good_p = round(random.uniform(70, 95), 2)
            mod_p = round(random.uniform(5, 100 - good_p), 2)
            attn_p = round(100 - good_p - mod_p, 2)
        elif ndvi_mean < min_val:
            health = 'Need Attention'
            attn_p = round(random.uniform(60, 90), 2)
            mod_p = round(random.uniform(5, 100 - attn_p), 2)
            good_p = round(100 - attn_p - mod_p, 2)
        else:
            health = 'Moderate'
            mod_p = round(random.uniform(50, 80), 2)
            good_p = round(random.uniform(10, 100 - mod_p), 2)
            attn_p = round(100 - mod_p - good_p, 2)
            
        total_px = random.randint(1000, 5000)
        px_good = int(total_px * (good_p / 100))
        px_mod = int(total_px * (mod_p / 100))
        px_attn = total_px - px_good - px_mod
        
        NDVIRecord.objects.create(
            plot=plot,
            date_recorded=current_date,
            ndvi_value=ndvi_mean,
            cloud_cover=round(random.uniform(0, 30), 2),
            health_status=health,
            
            # Hierarchy fields
            group_name=plot.group_name if plot.group_name else (plot.group.name if plot.group else (plot.farmer.section.division.factory_name.group.name if plot.farmer and plot.farmer.section and plot.farmer.section.division and plot.farmer.section.division.factory_name and plot.farmer.section.division.factory_name.group else None)),
            
            factory_name=plot.factory_name if plot.factory_name else (plot.factory.name if plot.factory else (plot.farmer.section.division.factory_name.name if plot.farmer and plot.farmer.section and plot.farmer.section.division and plot.farmer.section.division.factory_name else None)),
            
            division_name=plot.division_name if plot.division_name else (plot.division.name if plot.division else (plot.farmer.section.division.name if plot.farmer and plot.farmer.section and plot.farmer.section.division else None)),
            
            section_name=plot.section_name if plot.section_name else (plot.section.section_name if plot.section else (plot.farmer.section.section_name if plot.farmer and plot.farmer.section else None)),
            
            village_name=plot.village_name if plot.village_name else (plot.village.name if plot.village else (plot.farmer.village.name if plot.farmer and plot.farmer.village else None)),
            
            farmer_name=plot.farmer.name if plot.farmer else None,
            plot_name=plot.plot_code,
            
            crop_age_days=days_since_planting,
            stage=stage,
            ndvi_mean=ndvi_mean,
            ndvi_min=ndvi_min,
            ndvi_max=ndvi_max,
            thr_min=thr_min,
            thr_max=thr_max,
            good_percent=good_p,
            mod_percent=mod_p,
            attn_percent=attn_p,
            px_good=px_good,
            px_mod=px_mod,
            px_attn=px_attn,
            px_total=total_px
        )
        
        current_date += timedelta(days=15)

print("NDVI records generation completed successfully!")
