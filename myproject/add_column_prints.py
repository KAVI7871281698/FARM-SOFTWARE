with open(r"d:\Own Apps\Clients docs\Farm Signals\myproject\myapp\views.py", "r") as f:
    content = f.read()

# Add print for columns right after df is loaded
content = content.replace("df.columns = df.columns.astype(str).str.strip().str.lower()", "df.columns = df.columns.astype(str).str.strip().str.lower()\n            print(f\"DEBUG: Loaded file. Columns found: {list(df.columns)}\")")

# Also print exceptions
content = content.replace("messages.error(request, f'Error importing sections: {str(e)}')", "print(f\"DEBUG Error importing sections: {str(e)}\"); messages.error(request, f'Error importing sections: {str(e)}')")
content = content.replace("messages.error(request, f'Error importing divisions: {str(e)}')", "print(f\"DEBUG Error importing divisions: {str(e)}\"); messages.error(request, f'Error importing divisions: {str(e)}')")
content = content.replace("messages.error(request, f'Error importing villages: {str(e)}')", "print(f\"DEBUG Error importing villages: {str(e)}\"); messages.error(request, f'Error importing villages: {str(e)}')")
content = content.replace("messages.error(request, f'Error importing farmers: {str(e)}')", "print(f\"DEBUG Error importing farmers: {str(e)}\"); messages.error(request, f'Error importing farmers: {str(e)}')")

with open(r"d:\Own Apps\Clients docs\Farm Signals\myproject\myapp\views.py", "w") as f:
    f.write(content)
