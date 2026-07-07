with open(r"d:\Own Apps\Clients docs\Farm Signals\myproject\myapp\views.py", "r") as f:
    content = f.read()

# Fix add_village
content = content.replace(
    "Village.objects.create(",
    "if not division and section and section.division:\n                division = section.division.name\n            Village.objects.create("
)

# Fix edit_village
content = content.replace(
    "village.division = request.POST.get('division')",
    "village.division = request.POST.get('division') or (section.division.name if section and section.division else '')"
)

# Fix import_villages
content = content.replace(
    "'division': div_name if div_name != 'nan' else '',",
    "'division': div_name if div_name and div_name != 'nan' else (section.division.name if section and section.division else ''),"
)
content = content.replace(
    "if div_name and div_name != 'nan': vil.division = div_name",
    "if div_name and div_name != 'nan':\n                                vil.division = div_name\n                            elif section and section.division:\n                                vil.division = section.division.name"
)

# Fix import_farmers
# They have 'division=division' in add_farmer, let's fix add_farmer too.
content = content.replace(
    "Farmer.objects.create(",
    "if not division and section and section.division:\n              division = section.division.name\n          Farmer.objects.create("
)

with open(r"d:\Own Apps\Clients docs\Farm Signals\myproject\myapp\views.py", "w") as f:
    f.write(content)
