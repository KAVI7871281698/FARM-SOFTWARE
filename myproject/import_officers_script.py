import os
import django
import csv
import random
import string

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from myapp.models import Officer, Role, Factory, Division

def run():
    print("Starting officer import and fix (roles + user_id)...")
    
    officers_dict = {}
    
    # Read farm officers
    with open('farm_officers_rows (1).csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            officer_id = row['id']
            officers_dict[officer_id] = {
                'name': row['name'],
                'phone': row['phone'],
                'factory_code': row['factory_code'],
                'role_name': row['role'],
                'divisions': []
            }
            if row.get('division_code'):
                officers_dict[officer_id]['divisions'].append(row['division_code'])

    # Read officer divisions
    with open('officer_divisions_rows (2).csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            officer_id = row['officer_id']
            if officer_id in officers_dict:
                div_code = row['division_code']
                if div_code and div_code not in officers_dict[officer_id]['divisions']:
                    officers_dict[officer_id]['divisions'].append(div_code)

    updated_count = 0
    created_count = 0
    
    for oid, data in officers_dict.items():
        name = data['name'].strip()
        phone = data['phone'].strip()
        if not phone:
            phone = '9' + ''.join(random.choices(string.digits, k=9))
            
        email = f"{phone}@farmsignals.com"
        
        # Determine Role
        raw_role = data['role_name'].strip() if data['role_name'] else "officer"
        role = Role.objects.filter(name__iexact=raw_role).order_by('id').first()
        if not role:
            # Fallback create
            role, _ = Role.objects.get_or_create(name=raw_role.title())
            
        # Determine Divisions
        div_ids = []
        div_names = []
        division_objects = []
        
        for dcode in data['divisions']:
            d = Division.objects.filter(code__iexact=dcode).first()
            if not d:
                d = Division.objects.filter(name__iexact=dcode).first()
            if d:
                div_ids.append(str(d.id))
                div_names.append(d.name)
                division_objects.append(d)
                
        division_ids = "[" + ",".join(div_ids) + "]" if div_ids else "[]"
        division_names = ", ".join(div_names)
        
        # Determine Factory and Group
        factory_code = data['factory_code']
        fac = Factory.objects.filter(code__iexact=factory_code).first() if factory_code else None
        if not fac and factory_code:
            fac = Factory.objects.filter(name__iexact=factory_code).first()
            
        # Infer from division if needed
        if not fac and division_objects:
            fac = division_objects[0].factory_name
            
        group = fac.group if fac else None
        
        factory_ids = f"[{fac.id}]" if fac else "[]"
        factory_names = fac.name if fac else ""
        
        # user_id is the role name (e.g. 'officer', 'manager')
        user_id_val = role.name.replace(" ", "") if role and role.name else "User"
            
        officer = Officer.objects.filter(mobile=phone).first()
        if officer:
            # Update existing
            officer.name = name
            officer.user_id = user_id_val
            if not officer.email:
                officer.email = email
            officer.role = role
            officer.role_name = role.name
            if group:
                officer.group = group
                officer.group_name = group.name
            if fac:
                officer.factory_ids = factory_ids
                officer.factory_names = factory_names
            if div_ids:
                officer.division_ids = division_ids
                officer.division_names = division_names
            officer.save()
            updated_count += 1
        else:
            # Check if email is unique, else modify it
            while Officer.objects.filter(email=email).exists():
                email = f"user_{random.randint(1000,9999)}@farmsignals.com"
                
            officer = Officer(
                user_id=user_id_val,
                name=name,
                mobile=phone,
                email=email,
                role=role,
                role_name=role.name,
                group=group,
                group_name=group.name if group else None,
                factory_ids=factory_ids,
                factory_names=factory_names,
                division_ids=division_ids,
                division_names=division_names
            )
            officer.save()
            created_count += 1
            
    print(f"Fix completed! Created {created_count}, updated {updated_count} officers.")

if __name__ == '__main__':
    run()
