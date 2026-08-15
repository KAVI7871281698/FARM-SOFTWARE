import os
import sys
import django
import pandas as pd
import numpy as np
import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from myapp.models import Plot, Crop, Variety, Factory, SoilType
from django.db.models.signals import post_save
try:
    from myapp.models import create_surveys_on_plot_creation
except ImportError:
    pass

def safe_str(val):
    if pd.isna(val) or val == 'nan':
        return ''
    # If it's a float like 8000799343.0, convert to int first
    if isinstance(val, float):
        try:
            return str(int(val))
        except:
            return str(val)
    return str(val).strip()

def run():
    print("Starting data update...")
    
    try:
        post_save.disconnect(create_surveys_on_plot_creation, sender=Plot)
        print("Disconnected post_save signal on Plot.")
    except Exception as e:
        print("Failed to disconnect signal:", e)
        
    # 1. Update Factory information from 007- plots_rows.csv
    file_007 = "007- plots_rows.csv"
    if os.path.exists(file_007):
        df_plots = pd.read_csv(file_007)
        print(f"Loaded {len(df_plots)} rows from {file_007}")
        
        # Build factory map
        factories = {f.code: f for f in Factory.objects.all() if f.code}
        
        updates = 0
        for _, row in df_plots.iterrows():
            plot_no = safe_str(row.get('plot_no'))
            factory_code = safe_str(row.get('factory_code'))
            if plot_no and factory_code:
                try:
                    plot = Plot.objects.get(plot_code=plot_no)
                    if factory_code in factories:
                        fac = factories[factory_code]
                        if plot.factory_id != fac.id:
                            plot.factory = fac
                            plot.factory_name = fac.name
                            plot.save(update_fields=['factory', 'factory_name'])
                            updates += 1
                except Plot.DoesNotExist:
                    pass
        print(f"Updated factory info for {updates} plots.")
    else:
        print(f"{file_007} not found.")

    # 2. Update Crop, Variety, Crushing Season, Soil Type, Harvest Date from 008- plot_seasons_rows.csv
    file_008 = "008- plot_seasons_rows.csv"
    if os.path.exists(file_008):
        df_seasons = pd.read_csv(file_008)
        print(f"Loaded {len(df_seasons)} rows from {file_008}")
        
        updates = 0
        for _, row in df_seasons.iterrows():
            plot_no = safe_str(row.get('plot_no'))
            crop_name = safe_str(row.get('crop_name'))
            variety_name = safe_str(row.get('variety_name'))
            crushing_season = safe_str(row.get('crushing_season'))
            soil_type_str = safe_str(row.get('soil_type'))
            harvest_date_str = safe_str(row.get('harvest_date'))
            
            if plot_no:
                try:
                    plot = Plot.objects.get(plot_code=plot_no)
                    changed = False
                    
                    if crop_name:
                        crop, _ = Crop.objects.get_or_create(crop_name=crop_name)
                        if plot.crop_type_id != crop.id:
                            plot.crop_type = crop
                            changed = True
                            
                        if variety_name:
                            variety, _ = Variety.objects.get_or_create(
                                variety_name=variety_name,
                                defaults={'crop_type': crop}
                            )
                            if plot.variety_id != variety.id:
                                plot.variety = variety
                                changed = True
                                
                    if crushing_season and plot.crushing_season != crushing_season:
                        plot.crushing_season = crushing_season
                        changed = True

                    if soil_type_str:
                        # title case it so it matches better or just keep original
                        soil_type_str = soil_type_str.title()
                        soil_obj, _ = SoilType.objects.get_or_create(soil_name=soil_type_str)
                        if plot.soil_type_id != soil_obj.id:
                            plot.soil_type = soil_obj
                            changed = True

                    if harvest_date_str:
                        # try parse date YYYY-MM-DD
                        try:
                            # It might be in different format, assume standard ISO
                            parsed_date = pd.to_datetime(harvest_date_str).date()
                            if plot.harvest_date != parsed_date:
                                plot.harvest_date = parsed_date
                                changed = True
                        except:
                            pass
                        
                    if changed:
                        plot.save(update_fields=['crop_type', 'variety', 'crushing_season', 'soil_type', 'harvest_date'])
                        updates += 1
                except Plot.DoesNotExist:
                    pass
        print(f"Updated crop/variety/season/soil/harvest for {updates} plots.")
    else:
        print(f"{file_008} not found.")

if __name__ == '__main__':
    run()
