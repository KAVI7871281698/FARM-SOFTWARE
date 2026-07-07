with open("myapp/views.py", "a") as f:
    f.write('''
def import_divisions(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        try:
            if excel_file.name.endswith('.csv'):
                df = pd.read_csv(excel_file)
            else:
                df = pd.read_excel(excel_file)
            df.columns = df.columns.astype(str).str.strip().str.lower()
            
            imported_count = 0
            for index, row in df.iterrows():
                code = str(row.get('code', row.get('division code', ''))).strip()
                name = str(row.get('name', row.get('division name', ''))).strip()
                factory_code_col = str(row.get('factory_code', row.get('factory code', ''))).strip()
                
                if name and name != 'nan':
                    factory = Factory.objects.filter(code__iexact=factory_code_col).first() if factory_code_col and factory_code_col != 'nan' else None
                    if factory:
                        div, created = Division.objects.get_or_create(name=name, factory_name=factory, defaults={'code': code if code != 'nan' else ''})
                        if not created and code and code != 'nan':
                            div.code = code
                            div.save()
                        imported_count += 1
            if imported_count == 0:
                messages.error(request, f'No divisions imported. Columns found: {list(df.columns)}')
            else:
                messages.success(request, f'{imported_count} Divisions imported successfully!')
        except Exception as e:
            messages.error(request, f'Error importing divisions: {str(e)}')
    return redirect('divisions')

def import_sections(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        try:
            if excel_file.name.endswith('.csv'):
                df = pd.read_csv(excel_file)
            else:
                df = pd.read_excel(excel_file)
            df.columns = df.columns.astype(str).str.strip().str.lower()
            
            imported_count = 0
            for index, row in df.iterrows():
                code = str(row.get('section_code', row.get('section code', ''))).strip()
                name = str(row.get('section_name', row.get('section name', ''))).strip()
                desc = str(row.get('description', '')).strip()
                division_code = str(row.get('division_code', row.get('division code', ''))).strip()
                
                if name and name != 'nan':
                    division = Division.objects.filter(code__iexact=division_code).first() if division_code and division_code != 'nan' else None
                    if division:
                        sec, created = Section.objects.get_or_create(section_name=name, division=division, defaults={
                            'section_code': code if code != 'nan' else '',
                            'description': desc if desc != 'nan' else ''
                        })
                        if not created:
                            if code and code != 'nan': sec.section_code = code
                            if desc and desc != 'nan': sec.description = desc
                            sec.save()
                        imported_count += 1
            if imported_count == 0:
                messages.error(request, f'No sections imported. Columns found: {list(df.columns)}')
            else:
                messages.success(request, f'{imported_count} Sections imported successfully!')
        except Exception as e:
            messages.error(request, f'Error importing sections: {str(e)}')
    return redirect('sections')

def import_villages(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        try:
            if excel_file.name.endswith('.csv'):
                df = pd.read_csv(excel_file)
            else:
                df = pd.read_excel(excel_file)
            df.columns = df.columns.astype(str).str.strip().str.lower()
            
            imported_count = 0
            for index, row in df.iterrows():
                code = str(row.get('village_code', row.get('village code', ''))).strip()
                name = str(row.get('village_name', row.get('village name', ''))).strip()
                div_name = str(row.get('division', '')).strip()
                taluk = str(row.get('taluk', '')).strip()
                district = str(row.get('district', '')).strip()
                state = str(row.get('state', '')).strip()
                section_code = str(row.get('section_code', row.get('section code', ''))).strip()
                
                if name and name != 'nan':
                    section = Section.objects.filter(section_code__iexact=section_code).first() if section_code and section_code != 'nan' else None
                    if section:
                        vil, created = Village.objects.get_or_create(village_name=name, section=section, defaults={
                            'village_code': code if code != 'nan' else '',
                            'division': div_name if div_name != 'nan' else '',
                            'taluk': taluk if taluk != 'nan' else '',
                            'district': district if district != 'nan' else '',
                            'state': state if state != 'nan' else ''
                        })
                        if not created:
                            if code and code != 'nan': vil.village_code = code
                            if div_name and div_name != 'nan': vil.division = div_name
                            if taluk and taluk != 'nan': vil.taluk = taluk
                            if district and district != 'nan': vil.district = district
                            if state and state != 'nan': vil.state = state
                            vil.save()
                        imported_count += 1
            if imported_count == 0:
                messages.error(request, f'No villages imported. Columns found: {list(df.columns)}')
            else:
                messages.success(request, f'{imported_count} Villages imported successfully!')
        except Exception as e:
            messages.error(request, f'Error importing villages: {str(e)}')
    return redirect('villages')

def import_farmers(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        try:
            if excel_file.name.endswith('.csv'):
                df = pd.read_csv(excel_file)
            else:
                df = pd.read_excel(excel_file)
            df.columns = df.columns.astype(str).str.strip().str.lower()
            
            imported_count = 0
            for index, row in df.iterrows():
                code = str(row.get('farmer_code', row.get('farmer code', ''))).strip()
                name = str(row.get('name', row.get('farmer name', ''))).strip()
                father = str(row.get('father_name', row.get('father name', ''))).strip()
                phone = str(row.get('phone', row.get('phone number', ''))).strip()
                
                sec_code = str(row.get('section_code', row.get('section code', ''))).strip()
                vil_code = str(row.get('village_code', row.get('village code', ''))).strip()
                group_code = str(row.get('group_code', row.get('group code', ''))).strip()
                factory_code = str(row.get('factory_code', row.get('factory code', ''))).strip()
                
                if name and name != 'nan':
                    section = Section.objects.filter(section_code__iexact=sec_code).first() if sec_code and sec_code != 'nan' else None
                    village = Village.objects.filter(village_code__iexact=vil_code).first() if vil_code and vil_code != 'nan' else None
                    group = Group.objects.filter(code__iexact=group_code).first() if group_code and group_code != 'nan' else None
                    factory = Factory.objects.filter(code__iexact=factory_code).first() if factory_code and factory_code != 'nan' else None
                    
                    if section and village:
                        frm, created = Farmer.objects.get_or_create(name=name, phone=phone if phone != 'nan' else '', defaults={
                            'farmer_code': code if code != 'nan' else '',
                            'father_name': father if father != 'nan' else '',
                            'section': section,
                            'village': village,
                            'group': group,
                            'group_name': group.name if group else '',
                            'factory': factory,
                            'factory_name': factory.name if factory else ''
                        })
                        if not created:
                            frm.farmer_code = code if code != 'nan' else frm.farmer_code
                            frm.father_name = father if father != 'nan' else frm.father_name
                            frm.section = section
                            frm.village = village
                            frm.group = group
                            frm.group_name = group.name if group else ''
                            frm.factory = factory
                            frm.factory_name = factory.name if factory else ''
                            frm.save()
                        imported_count += 1
            if imported_count == 0:
                messages.error(request, f'No farmers imported. Columns found: {list(df.columns)}')
            else:
                messages.success(request, f'{imported_count} Farmers imported successfully!')
        except Exception as e:
            messages.error(request, f'Error importing farmers: {str(e)}')
    return redirect('users')
''')
