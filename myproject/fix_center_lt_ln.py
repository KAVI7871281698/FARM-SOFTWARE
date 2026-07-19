import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Plot

def run():
    plots = Plot.objects.exclude(center_lt_ln__isnull=True)
    count = 0
    for p in plots:
        c = p.center_lt_ln
        if isinstance(c, list) and len(c) == 1:
            val = c[0]
            if isinstance(val, str) and ',' in val:
                parts = val.split(',')
                try:
                    lat = float(parts[0].strip())
                    lon = float(parts[1].strip())
                    p.center_lt_ln = [lat, lon]
                    p.save()
                    count += 1
                except:
                    pass
    print(f"Fixed center_lt_ln for {count} plots.")

if __name__ == '__main__':
    run()
