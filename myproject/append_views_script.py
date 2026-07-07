import pandas as pd
from django.contrib import messages

def import_groups(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        try:
            df = pd.read_excel(excel_file)
            for index, row in df.iterrows():
                code = str(row.get('code', row.get('Code', '')))
                name = str(row.get('name', row.get('Name', '')))
                if name and name != 'nan':
                    group, created = Group.objects.get_or_create(name=name, defaults={'code': code if code != 'nan' else ''})
                    if not created and code and code != 'nan':
                        group.code = code
                        group.save()
            messages.success(request, 'Groups imported successfully!')
        except Exception as e:
            messages.error(request, f'Error importing groups: {str(e)}')
    return redirect('groups')

def import_factories(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        try:
            df = pd.read_excel(excel_file)
            for index, row in df.iterrows():
                group_name = str(row.get('group_name', row.get('Group Name', '')))
                code = str(row.get('code', row.get('Code', '')))
                name = str(row.get('name', row.get('Name', '')))
                location = str(row.get('location_LatLong', row.get('Location', '')))
                capacity = str(row.get('crushing_capacity', row.get('Capacity', '')))
                
                if name and name != 'nan' and group_name and group_name != 'nan':
                    group = Group.objects.filter(name=group_name).first()
                    if group:
                        factory, created = Factory.objects.get_or_create(name=name, group=group, defaults={
                            'code': code if code != 'nan' else '',
                            'location_LatLong': location if location != 'nan' else '',
                            'crushing_capacity': capacity if capacity != 'nan' else ''
                        })
                        if not created:
                            factory.code = code if code != 'nan' else factory.code
                            factory.location_LatLong = location if location != 'nan' else factory.location_LatLong
                            factory.crushing_capacity = capacity if capacity != 'nan' else factory.crushing_capacity
                            factory.save()
            messages.success(request, 'Factories imported successfully!')
        except Exception as e:
            messages.error(request, f'Error importing factories: {str(e)}')
    return redirect('factories')
