import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from myapp.models import Officer, Division, WorkAssign

def run():
    officers = Officer.objects.all()
    count = 0
    for officer in officers:
        if not officer.division_ids:
            continue
            
        div_ids_str = str(officer.division_ids).replace('[', '').replace(']', '').replace("'", "").replace('"', "")
        div_ids = [x.strip() for x in div_ids_str.split(',') if x.strip()]
        
        for div_id in div_ids:
            try:
                division = Division.objects.get(id=int(div_id))
                # Check if work assign already exists
                exists = WorkAssign.objects.filter(officer=officer, division=division.name).exists()
                if not exists:
                    WorkAssign.objects.create(
                        officer=officer,
                        division=division.name,
                        status="active"
                    )
                    count += 1
                    print(f"Created WorkAssign for Officer {officer.name} in Division {division.name}")
            except Exception as e:
                print(f"Error processing division {div_id} for officer {officer.name}: {e}")

    print(f"Total WorkAssign records created: {count}")

if __name__ == '__main__':
    run()
