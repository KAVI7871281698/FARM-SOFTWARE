from django.db import models

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "role"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_name = None
        if not is_new:
            try:
                old_name = Role.objects.get(pk=self.pk).name
            except Role.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        if not is_new and old_name and old_name != self.name:
            new_user_id = self.name.replace(" ", "")
            self.officer_set.all().update(user_id=new_user_id, role_name=self.name)

class Officer(models.Model):
    user_id = models.CharField(max_length=50, null=True, blank=True)
    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100, unique=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True)
    role_name = models.CharField(max_length=50, null=True, blank=True)
    permissions = models.JSONField(default=list, blank=True, null=True)
    group = models.ForeignKey('Group', on_delete=models.SET_NULL, null=True, blank=True)
    factory_ids = models.CharField(max_length=255, blank=True, null=True)
    factory_names = models.CharField(max_length=500, blank=True, null=True)
    division_ids = models.CharField(max_length=255, blank=True, null=True)
    division_names = models.CharField(max_length=500, blank=True, null=True)
    section_ids = models.CharField(max_length=255, blank=True, null=True)
    section_names = models.CharField(max_length=500, blank=True, null=True)
    latitude = models.CharField(max_length=100, blank=True, null=True)
    longitude = models.CharField(max_length=100, blank=True, null=True)
    device_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "officer"

    def save(self, *args, **kwargs):
        if self.role and self.role.name:
            self.role_name = self.role.name
            
        if not self.user_id:
            role_name_formatted = self.role.name.replace(" ", "") if self.role and self.role.name else "User"
            self.user_id = f"{role_name_formatted}"
        
        if not self.password or self.password == 'default123':
            import random
            import string
            chars = string.ascii_uppercase + string.digits
            self.password = ''.join(random.choices(chars, k=6))
            
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Section(models.Model):
    section_code = models.CharField(max_length=50, unique=True, blank=True)
    section_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    division = models.ForeignKey('Division', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "section"

    def save(self, *args, **kwargs):
        if not self.section_code:
            last_section = Section.objects.all().order_by('id').last()
            if last_section:
                last_id = last_section.id
                self.section_code = f"SEC-{last_id + 1:03d}"
            else:
                self.section_code = "SEC-001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.section_code} - {self.section_name}"

class Village(models.Model):
    village_code = models.CharField(max_length=50, unique=True, blank=True)
    village_name = models.CharField(max_length=100)
    division = models.CharField(max_length=100, blank=True, null=True)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="villages")
    taluk = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, default="active")
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "village"

    def save(self, *args, **kwargs):
        if not self.village_code:
            last_village = Village.objects.all().order_by('id').last()
            if last_village:
                last_id = last_village.id
                self.village_code = f"VIL-{last_id + 1:03d}"
            else:
                self.village_code = "VIL-001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.village_code} - {self.village_name}"

class Farmer(models.Model):
    farmer_code = models.CharField(max_length=50, unique=True, blank=True)
    name = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    division = models.CharField(max_length=100, blank=True, null=True)
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, related_name="farmers")
    village = models.ForeignKey(Village, on_delete=models.SET_NULL, null=True, related_name="farmers")

    class Meta:
        db_table = "farmer"

    def save(self, *args, **kwargs):
        if not self.farmer_code:
            last_farmer = Farmer.objects.all().order_by('id').last()
            if last_farmer:
                last_id = last_farmer.id
                self.farmer_code = f"FAR-{last_id + 1:03d}"
            else:
                self.farmer_code = "FAR-001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.farmer_code} - {self.name}"

class Variety(models.Model):
    variety_code = models.CharField(max_length=50, unique=True, blank=True)
    crop_type = models.CharField(max_length=100)
    variety_name = models.CharField(max_length=150)
    season = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = "variety"

    def save(self, *args, **kwargs):
        if not self.variety_code:
            last_variety = Variety.objects.all().order_by('id').last()
            if last_variety:
                last_id = last_variety.id
                self.variety_code = f"VAR-{last_id + 1:03d}"
            else:
                self.variety_code = "VAR-001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.variety_code} - {self.variety_name}"

class Group(models.Model):
    code = models.CharField(max_length=50, unique=True, blank=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "group_master"

    def save(self, *args, **kwargs):
        if not self.code:
            last_group = Group.objects.all().order_by('id').last()
            if last_group:
                last_id = last_group.id
                self.code = f"GRP-{last_id + 1:03d}"
            else:
                self.code = "GRP-001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"

class Factory(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="factories")
    code = models.CharField(max_length=50, unique=True, blank=True)
    name = models.CharField(max_length=100)
    location_LatLong = models.CharField(max_length=200, blank=True, null=True)
    crushing_capacity = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = "factory"

    def save(self, *args, **kwargs):
        if not self.code:
            last_factory = Factory.objects.all().order_by('id').last()
            if last_factory:
                last_id = last_factory.id
                self.code = f"FAC-{last_id + 1:03d}"
            else:
                self.code = "FAC-001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"

class Division(models.Model):
    factory_name = models.ForeignKey(Factory, on_delete=models.CASCADE, related_name="divisions")
    code = models.CharField(max_length=50, unique=True, blank=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "division"

    def save(self, *args, **kwargs):
        if not self.code:
            last_division = Division.objects.all().order_by('id').last()
            if last_division:
                last_id = last_division.id
                self.code = f"DIV-{last_id + 1:03d}"
            else:
                self.code = "DIV-001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"

class WorkAssign(models.Model):
    work_assign_code = models.CharField(max_length=50, unique=True, blank=True)
    division = models.CharField(max_length=100, blank=True, null=True)
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, related_name="work_assigns")
    village = models.ForeignKey(Village, on_delete=models.SET_NULL, null=True, related_name="work_assigns")
    officer = models.ForeignKey(Officer, on_delete=models.SET_NULL, null=True, related_name="work_assigns")
    status = models.CharField(max_length=20, default="active")
    latitude = models.CharField(max_length=100, blank=True, null=True)
    longitude = models.CharField(max_length=100, blank=True, null=True)
    device_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "work_assign"

    def save(self, *args, **kwargs):
        if not self.work_assign_code:
            last_assign = WorkAssign.objects.all().order_by('id').last()
            if last_assign:
                last_id = last_assign.id
                self.work_assign_code = f"WRK-{last_id + 1:03d}"
            else:
                self.work_assign_code = "WRK-001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.work_assign_code} - {self.officer.name if self.officer else 'Unassigned'}"
