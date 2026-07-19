code = """
@receiver(post_save, sender=Officer)
def auto_assign_work_on_officer_save(sender, instance, created, **kwargs):
    if instance.division_ids:
        div_ids_str = str(instance.division_ids).replace('[', '').replace(']', '').replace(\"'\", \"\").replace('\"', \"\")
        div_ids = [x.strip() for x in div_ids_str.split(',') if x.strip()]
        
        for div_id in div_ids:
            try:
                division = Division.objects.get(id=int(div_id))
                exists = WorkAssign.objects.filter(officer=instance, division=division.name).exists()
                if not exists:
                    WorkAssign.objects.create(
                        officer=instance,
                        division=division.name,
                        status="active"
                    )
            except Exception as e:
                pass
"""

with open('myapp/models.py', 'a') as f:
    f.write(code)
