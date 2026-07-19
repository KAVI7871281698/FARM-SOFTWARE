import os

filepath = r"d:\Own Apps\Clients docs\Farm Signals\myproject\myapp\views.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update plots_query in ndvi_dashboard
old_query = "plots_query = Plot.objects.filter(Q(center_lt_ln__isnull=False) | Q(boundaries__isnull=False)).distinct()"
new_query = """from django.db.models import Prefetch
    plots_query = Plot.objects.filter(Q(center_lt_ln__isnull=False) | Q(boundaries__isnull=False)).select_related('farmer').prefetch_related(
        Prefetch('scouting_logs', queryset=ScoutingLog.objects.order_by('-created_at')),
        Prefetch('ndvi_records', queryset=NDVIRecord.objects.order_by('-date_recorded'))
    ).distinct()"""
content = content.replace(old_query, new_query)

# 2. Update loop
old_loop_1 = "latest_scout = plot.scouting_logs.order_by('-created_at').first()"
new_loop_1 = """scouts = list(plot.scouting_logs.all())
        latest_scout = scouts[0] if scouts else None"""
content = content.replace(old_loop_1, new_loop_1)

old_loop_2 = "latest_ndvi = plot.ndvi_records.order_by('-date_recorded').first()"
new_loop_2 = """ndvis = list(plot.ndvi_records.all())
        latest_ndvi = ndvis[0] if ndvis else None"""
content = content.replace(old_loop_2, new_loop_2)

# 3. Update lat/lng parsing logic
old_parsing = """        lat = None
        lng = None
        if isinstance(plot.center_lt_ln, dict):
            lat = plot.center_lt_ln.get('lat', 0)
            lng = plot.center_lt_ln.get('lng', 0)
        elif plot.center_lt_ln:
            try:
                import json
                parsed = json.loads(plot.center_lt_ln.replace("'", '"'))
            except:
                try:
                    import ast
                    parsed = ast.literal_eval(plot.center_lt_ln)
                except:
                    parsed = None
                    
            if isinstance(parsed, dict):
                lat = parsed.get('lat', 0)
                lng = parsed.get('lng', 0)
            elif isinstance(parsed, list) and len(parsed) >= 2:
                lat = float(parsed[0])
                lng = float(parsed[1])
            elif isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], str) and ',' in parsed[0]:
                parts = parsed[0].split(',')
                lat = float(parts[0].strip())
                lng = float(parts[1].strip())"""

new_parsing = """        lat = None
        lng = None
        if isinstance(plot.center_lt_ln, list) and len(plot.center_lt_ln) >= 2:
            lat = float(plot.center_lt_ln[0])
            lng = float(plot.center_lt_ln[1])
        elif isinstance(plot.center_lt_ln, dict):
            lat = float(plot.center_lt_ln.get('lat', 0))
            lng = float(plot.center_lt_ln.get('lng', 0))
        elif plot.center_lt_ln:
            try:
                import json
                if isinstance(plot.center_lt_ln, str):
                    parsed = json.loads(plot.center_lt_ln.replace("'", '"'))
                else:
                    parsed = plot.center_lt_ln
                if isinstance(parsed, list) and len(parsed) >= 2:
                    lat = float(parsed[0])
                    lng = float(parsed[1])
                elif isinstance(parsed, dict):
                    lat = float(parsed.get('lat', 0))
                    lng = float(parsed.get('lng', 0))
            except:
                pass"""
content = content.replace(old_parsing, new_parsing)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Optimization of ndvi_dashboard complete.")
