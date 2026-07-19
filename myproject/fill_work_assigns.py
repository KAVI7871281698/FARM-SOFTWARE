import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from myapp.models import Officer, Division, Section, Village, WorkAssign

def run():
    print("Clearing old WorkAssigns...")
    WorkAssign.objects.all().delete()
    
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
                
                # Find all sections for this division
                sections = Section.objects.filter(division=division)
                
                if not sections.exists():
                    # No sections, just assign the division
                    WorkAssign.objects.create(
                        officer=officer,
                        division=division.name,
                        status="active"
                    )
                    count += 1
                else:
                    for section in sections:
                        # Find all villages for this section
                        villages = Village.objects.filter(section=section)
                        
                        if not villages.exists():
                            # No villages, just assign up to section
                            WorkAssign.objects.create(
                                officer=officer,
                                division=division.name,
                                section=section,
                                status="active"
                            )
                            count += 1
                        else:
                            # Create an assignment for every village
                            for village in villages:
                                WorkAssign.objects.create(
                                    officer=officer,
                                    division=division.name,
                                    section=section,
                                    village=village,
                                    status="active"
                                )
                                count += 1
                                
            except Exception as e:
                print(f"Error processing division {div_id} for officer {officer.name}: {e}")

    print(f"Total WorkAssign records created: {count}")

if __name__ == '__main__':
    run()
