with open(r"d:\Own Apps\Clients docs\Farm Signals\myproject\myapp\views.py", "r") as f:
    content = f.read()

# Fix syntax errors injected by powershell
content = content.replace("print(fDEBUG: No divisions imported. Columns: {list(df.columns)});", 'print(f"DEBUG: No divisions imported. Columns: {list(df.columns)}");')
content = content.replace("print(fDEBUG: No sections imported. Columns: {list(df.columns)});", 'print(f"DEBUG: No sections imported. Columns: {list(df.columns)}");')
content = content.replace("print(fDEBUG: No villages imported. Columns: {list(df.columns)});", 'print(f"DEBUG: No villages imported. Columns: {list(df.columns)}");')
content = content.replace("print(fDEBUG: No farmers imported. Columns: {list(df.columns)});", 'print(f"DEBUG: No farmers imported. Columns: {list(df.columns)}");')
# Clean up any messed up ones
content = content.replace("print(f\"\"DEBUG", 'print(f"DEBUG')

with open(r"d:\Own Apps\Clients docs\Farm Signals\myproject\myapp\views.py", "w") as f:
    f.write(content)
