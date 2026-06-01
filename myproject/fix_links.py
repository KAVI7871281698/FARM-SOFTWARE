import os
import re

template_dir = r"d:\Own Apps\Clients docs\myproject\myapp\templates"
pages = [
    "dashboard", "field_intelligence", "analytics", "ndvi_monitoring", 
    "scouting", "reports", "settings", "users", "villages", "sections", 
    "varieties", "plots", "surveys", "index", "officers",
    "add_farmer", "add_officer", "add_plots", "add_section", "add_survey",
    "add_user", "add_variety", "add_village"
]

for filename in os.listdir(template_dir):
    if filename.endswith(".html"):
        filepath = os.path.join(template_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modified = content
        for page in pages:
            # Replace href="page.html" with href="{% url 'page' %}"
            modified = re.sub(rf'href="{page}\.html"', f'href="{{% url \'{page}\' %}}"', modified)
            # Just in case some are href="page"
            if page != "index":
                modified = re.sub(rf'href="{page}"', f'href="{{% url \'{page}\' %}}"', modified)
            
        if modified != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(modified)
            print(f"Updated {filename}")
