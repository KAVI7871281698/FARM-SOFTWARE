import os

filepath = r"d:\Own Apps\Clients docs\Farm Signals\myproject\myapp\views.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    ("farmers = Farmer.objects.all()", "farmers = Farmer.objects.select_related('division', 'section', 'village', 'group', 'factory').all()"),
    ("plots = Plot.objects.all()", "plots = Plot.objects.select_related('farmer', 'division', 'section', 'village', 'crop_type', 'variety', 'soil_type', 'group', 'factory', 'officer').all()"),
    ("officers = Officer.objects.all()", "officers = Officer.objects.select_related('role', 'division', 'group', 'factory', 'section').all()"),
    ("logs = ScoutingLog.objects.all()", "logs = ScoutingLog.objects.select_related('plot', 'plot__farmer', 'scout', 'officer').all()"),
    ("work_assigns = WorkAssign.objects.all()", "work_assigns = WorkAssign.objects.select_related('officer', 'division', 'section', 'village').all()"),
    ("villages = Village.objects.all()", "villages = Village.objects.select_related('division', 'section').all()"),
    ("sections = Section.objects.all()", "sections = Section.objects.select_related('division').all()"),
]

for old, new in replacements:
    content = content.replace(old, new)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Optimization complete.")
