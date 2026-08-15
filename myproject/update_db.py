import os
import sys
import django
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from myapp.models import Plot, Crop, Variety, Factory

def run():
    print("Starting data update...")
    
    # 1. Update Factory information from 007- plots_rows.csv
    file_007 = "007- plots_rows.csv"
    if os.path.exists(file_007):
        df_plots = pd.read_csv(file_007)
        print(f"Loaded {len(df_plots)} rows from {file_007}")
        
        # Build factory map
        factories = {f.code: f for f in Factory.objects.all() if f.code}
        
        updates = 0
        for _, row in df_plots.iterrows():
            plot_no = str(row.get('plot_no', ''))
            factory_code = str(row.get('factory_code', ''))
            if plot_no and factory_code and factory_code != 'nan':
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

    # 2. Update Crop, Variety, Crushing Season from 008- plot_seasons_rows.csv
    file_008 = "008- plot_seasons_rows.csv"
    if os.path.exists(file_008):
        df_seasons = pd.read_csv(file_008)
        print(f"Loaded {len(df_seasons)} rows from {file_008}")
        
        updates = 0
        for _, row in df_seasons.iterrows():
            plot_no = str(row.get('plot_no', ''))
            crop_name = str(row.get('crop_name', ''))
            variety_name = str(row.get('variety_name', ''))
            crushing_season = str(row.get('crushing_season', ''))
            
            if plot_no and plot_no != 'nan':
                try:
                    plot = Plot.objects.get(plot_code=plot_no)
                    changed = False
                    
                    if crop_name and crop_name != 'nan':
                        crop, created = Crop.objects.get_or_create(crop_name=crop_name)
                        if plot.crop_type_id != crop.id:
                            plot.crop_type = crop
                            changed = True
                            
                        if variety_name and variety_name != 'nan':
                            variety, v_created = Variety.objects.get_or_create(
                                variety_name=variety_name,
                                defaults={'crop_type': crop}
                            )
                            if plot.variety_id != variety.id:
                                plot.variety = variety
                                changed = True
                                
                    if crushing_season and crushing_season != 'nan' and plot.crushing_season != crushing_season:
                        plot.crushing_season = crushing_season
                        changed = True
                        
                    if changed:
                        plot.save(update_fields=['crop_type', 'variety', 'crushing_season'])
                        updates += 1
                except Plot.DoesNotExist:
                    pass
        print(f"Updated crop/variety/season for {updates} plots.")
    else:
        print(f"{file_008} not found.")

if __name__ == '__main__':
    run()
