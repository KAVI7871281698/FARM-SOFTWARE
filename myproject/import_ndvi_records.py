import os
import django
import csv
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Plot, NDVIRecord

def parse_date(date_str):
    if not date_str:
        return None
    try:
        # Expected format: DD-MM-YYYY
        return datetime.strptime(date_str.strip(), "%d-%m-%Y").date()
    except:
        return None

def parse_float(val):
    if not val:
        return None
    try:
        return float(val.strip())
    except:
        return None

def parse_int(val):
    if not val:
        return None
    try:
        return int(val.strip())
    except:
        return None

def run():
    file_path = '011a- ndvi_observations_rows.csv'
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    # Pre-fetch all plots for fast lookup
    plot_map = {p.plot_code: p for p in Plot.objects.all() if p.plot_code}
    
    records_to_create = []
    missing_plots = set()

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            plot_no = row.get('plot_no', '').strip()
            
            if not plot_no or plot_no not in plot_map:
                missing_plots.add(plot_no)
                continue
                
            plot = plot_map[plot_no]
            obs_date = parse_date(row.get('obs_date'))
            
            if not obs_date:
                continue
                
            # Default ndvi_value to ndvi_mean, or 0 if missing (as it is required)
            ndvi_val = parse_float(row.get('ndvi_mean'))
            if ndvi_val is None:
                ndvi_val = 0.0

            health_status = row.get('health_status', '').strip()
            if not health_status:
                health_status = "Unknown"

            record = NDVIRecord(
                plot=plot,
                date_recorded=obs_date,
                ndvi_value=ndvi_val,
                health_status=health_status,
                crop_age_days=parse_int(row.get('crop_age_days')),
                stage=row.get('crop_stage', '').strip(),
                ndvi_mean=ndvi_val,
                ndvi_min=parse_float(row.get('ndvi_min')),
                ndvi_max=parse_float(row.get('ndvi_max')),
                thr_min=parse_float(row.get('ndvi_thr_min')),
                thr_max=parse_float(row.get('ndvi_thr_max')),
                good_percent=parse_float(row.get('pct_good')),
                mod_percent=parse_float(row.get('pct_moderate')),
                attn_percent=parse_float(row.get('pct_attention')),
                px_good=parse_int(row.get('px_good')),
                px_mod=parse_int(row.get('px_moderate')),
                px_attn=parse_int(row.get('px_attention')),
                px_total=parse_int(row.get('px_total'))
            )
            records_to_create.append(record)

    # Clear old records to avoid duplicates if re-running
    print("Clearing old NDVIRecord entries...")
    NDVIRecord.objects.all().delete()
    
    print(f"Bulk creating {len(records_to_create)} records...")
    # Use bulk_create for massive speed up
    batch_size = 1000
    NDVIRecord.objects.bulk_create(records_to_create, batch_size=batch_size)
    
    print(f"Finished successfully. Imported {len(records_to_create)} NDVI records.")
    if missing_plots:
        print(f"Could not find matching plots for {len(missing_plots)} plot numbers.")

if __name__ == '__main__':
    run()
