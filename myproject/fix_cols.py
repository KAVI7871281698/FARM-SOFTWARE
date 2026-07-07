with open(r"d:\Own Apps\Clients docs\Farm Signals\myproject\myapp\views.py", "r") as f:
    content = f.read()

# Sections
content = content.replace("code = str(row.get('section_code', row.get('section code', ''))).strip()", 
                          "code = str(row.get('section_code', row.get('section code', row.get('code', '')))).strip()")
content = content.replace("name = str(row.get('section_name', row.get('section name', ''))).strip()", 
                          "name = str(row.get('section_name', row.get('section name', row.get('name', '')))).strip()")

# Villages
content = content.replace("code = str(row.get('village_code', row.get('village code', ''))).strip()", 
                          "code = str(row.get('village_code', row.get('village code', row.get('code', '')))).strip()")
content = content.replace("name = str(row.get('village_name', row.get('village name', ''))).strip()", 
                          "name = str(row.get('village_name', row.get('village name', row.get('name', '')))).strip()")

# Farmers
content = content.replace("code = str(row.get('farmer_code', row.get('farmer code', ''))).strip()", 
                          "code = str(row.get('farmer_code', row.get('farmer code', row.get('code', '')))).strip()")
# Farmer name already has row.get('name', ...)
content = content.replace("name = str(row.get('name', row.get('farmer name', ''))).strip()", 
                          "name = str(row.get('name', row.get('farmer name', ''))).strip()") # No change needed here if name is primary

with open(r"d:\Own Apps\Clients docs\Farm Signals\myproject\myapp\views.py", "w") as f:
    f.write(content)
