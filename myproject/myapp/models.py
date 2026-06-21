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
    group_name = models.CharField(max_length=100, blank=True, null=True)
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
    group = models.ForeignKey('Group', on_delete=models.SET_NULL, null=True, blank=True)
    group_name = models.CharField(max_length=100, blank=True, null=True)
    factory = models.ForeignKey('Factory', on_delete=models.SET_NULL, null=True, blank=True)
    factory_name = models.CharField(max_length=100, blank=True, null=True)

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

class Crop(models.Model):
    crop_code = models.CharField(max_length=50, unique=True, blank=True)
    crop_name = models.CharField(max_length=150)

    class Meta:
        db_table = "crop"

    def save(self, *args, **kwargs):
        if not self.crop_code:
            last_crop = Crop.objects.all().order_by('id').last()
            if last_crop:
                last_id = last_crop.id
                self.crop_code = f"CRP-{last_id + 1:03d}"
            else:
                self.crop_code = "CRP-001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.crop_code} - {self.crop_name}"

class Plot(models.Model):
    plot_code = models.CharField(max_length=50, unique=True, blank=True)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="plots")
    division = models.ForeignKey('Division', on_delete=models.SET_NULL, null=True, blank=True)
    division_name = models.CharField(max_length=100, blank=True, null=True)
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True)
    section_name = models.CharField(max_length=100, blank=True, null=True)
    village = models.ForeignKey(Village, on_delete=models.SET_NULL, null=True, blank=True)
    village_name = models.CharField(max_length=100, blank=True, null=True)
    crop_type = models.ForeignKey(Crop, on_delete=models.SET_NULL, null=True, blank=True)
    variety = models.ForeignKey('Variety', on_delete=models.SET_NULL, null=True, blank=True)
    planting_date = models.DateField(null=True, blank=True)
    area_acre = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=50, default="Not Mapped")
    soil_type = models.ForeignKey('SoilType', on_delete=models.SET_NULL, null=True, blank=True)
    latitude = models.JSONField(blank=True, null=True)
    longitude = models.JSONField(blank=True, null=True)
    center_lt_ln = models.JSONField(blank=True, null=True)
    device_id = models.CharField(max_length=255, blank=True, null=True)
    gps_area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    planting_season = models.CharField(max_length=100, null=True, blank=True)
    crushing_season = models.CharField(max_length=100, null=True, blank=True)
    plot_type = models.CharField(max_length=100, null=True, blank=True)
    irrigation_type = models.CharField(max_length=100, null=True, blank=True)
    water_source = models.CharField(max_length=100, null=True, blank=True)
    seed_type = models.CharField(max_length=100, null=True, blank=True)
    spacing_ft = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    harvest_date = models.DateField(null=True, blank=True)
    production_t = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    yield_ton_acre = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    group = models.ForeignKey('Group', on_delete=models.SET_NULL, null=True, blank=True)
    group_name = models.CharField(max_length=100, blank=True, null=True)
    factory = models.ForeignKey('Factory', on_delete=models.SET_NULL, null=True, blank=True)
    factory_name = models.CharField(max_length=100, blank=True, null=True)
    officer = models.ForeignKey('Officer', on_delete=models.SET_NULL, null=True, blank=True, related_name="added_plots")
    boundary_image = models.JSONField(blank=True, null=True)
    boundaries = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = "plot"

    def save(self, *args, **kwargs):
        if not self.plot_code:
            last_plot = Plot.objects.all().order_by('id').last()
            if last_plot:
                last_id = last_plot.id
                self.plot_code = f"PLT-{last_id + 1:04d}"
            else:
                self.plot_code = "PLT-0001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.plot_code} - {self.farmer.name if self.farmer else ''}"

class Variety(models.Model):
    variety_code = models.CharField(max_length=50, unique=True, blank=True)
    variety_name = models.CharField(max_length=150)
    crop_type = models.ForeignKey(Crop, on_delete=models.SET_NULL, null=True, blank=True, related_name="varieties")

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

class FieldMapping(models.Model):
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="field_mappings")
    farmer_code = models.CharField(max_length=50, blank=True, null=True)
    plot = models.ForeignKey(Plot, on_delete=models.CASCADE, related_name="field_mappings")
    
    # Hierarchy
    division = models.CharField(max_length=100, blank=True, null=True)
    section = models.CharField(max_length=100, blank=True, null=True)
    village = models.CharField(max_length=100, blank=True, null=True)
    group = models.ForeignKey('Group', on_delete=models.SET_NULL, null=True, blank=True)
    group_name = models.CharField(max_length=100, blank=True, null=True)
    factory = models.ForeignKey('Factory', on_delete=models.SET_NULL, null=True, blank=True)
    factory_name = models.CharField(max_length=100, blank=True, null=True)
    
    # Mapping details
    boundary = models.JSONField(blank=True, null=True) # To store JSON polygon
    
    # Images
    img1 = models.ImageField(upload_to='field_images/', blank=True, null=True)
    img2 = models.ImageField(upload_to='field_images/', blank=True, null=True)
    img3 = models.ImageField(upload_to='field_images/', blank=True, null=True)
    
    # Tracking
    officer = models.ForeignKey('Officer', on_delete=models.SET_NULL, null=True, blank=True)
    officer_name = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "field_mapping"

    def __str__(self):
        return f"Mapping for Plot: {self.plot.plot_code} - {self.farmer.name}"

class SoilType(models.Model):
    soil_code = models.CharField(max_length=50, unique=True, blank=True)
    soil_name = models.CharField(max_length=150)

    class Meta:
        db_table = "soil_type"

    def save(self, *args, **kwargs):
        if not self.soil_code:
            last_soil = SoilType.objects.all().order_by('id').last()
            if last_soil:
                last_id = last_soil.id
                self.soil_code = f"SOIL-{last_id + 1:03d}"
            else:
                self.soil_code = "SOIL-001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.soil_code} - {self.soil_name}"

class ScoutingLog(models.Model):
    # Hierarchy
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)
    group_name = models.CharField(max_length=100, blank=True, null=True)
    factory = models.ForeignKey(Factory, on_delete=models.SET_NULL, null=True, blank=True)
    division = models.ForeignKey(Division, on_delete=models.SET_NULL, null=True, blank=True)
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True)
    village = models.ForeignKey(Village, on_delete=models.SET_NULL, null=True, blank=True)
    plot = models.ForeignKey(Plot, on_delete=models.CASCADE, related_name="scouting_logs")
    officer = models.ForeignKey(Officer, on_delete=models.SET_NULL, null=True, blank=True)

    # Crop Monitoring
    plant_height = models.CharField(max_length=100, blank=True, null=True)
    growth_stage = models.CharField(max_length=100, blank=True, null=True)

    # Pest Inspection
    pest_presence = models.BooleanField(default=False)
    pest_type = models.CharField(max_length=150, blank=True, null=True)
    pest_severity = models.CharField(max_length=50, blank=True, null=True) # Low, Medium, High

    # Disease Detection
    disease_presence = models.BooleanField(default=False)
    disease_type = models.CharField(max_length=150, blank=True, null=True)
    disease_photo = models.ImageField(upload_to='scouting_photos/', blank=True, null=True)

    # Irrigation Monitoring
    water_sufficiency = models.CharField(max_length=100, blank=True, null=True)
    water_stress_symptoms = models.BooleanField(default=False)

    # Nutrient Deficiency Check
    nutrient_deficiency = models.BooleanField(default=False)
    deficiency_symptoms = models.CharField(max_length=200, blank=True, null=True) # e.g. N, P, K
    fertilizer_recommendation = models.TextField(blank=True, null=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "scouting_log"

    def __str__(self):
        return f"Scouting for Plot {self.plot.plot_code} on {self.created_at.strftime('%Y-%m-%d')}"

class Survey(models.Model):
    survey_id = models.CharField(max_length=50, unique=True, blank=True)
    title = models.CharField(max_length=200, blank=True, null=True)
    plot = models.ForeignKey(Plot, on_delete=models.CASCADE, related_name="surveys")
    officer = models.ForeignKey(Officer, on_delete=models.SET_NULL, null=True, blank=True, related_name="surveys")
    survey_stage = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    survey_month = models.CharField(max_length=50, blank=True, null=True)
    number_of_days = models.IntegerField(default=0)
    allocated_dates = models.JSONField(blank=True, null=True)
    status = models.CharField(max_length=50, default="Active")
    completion_percentage = models.IntegerField(default=0)

    # Newly added fields
    weed_infestation = models.CharField(max_length=100, blank=True, null=True)
    tillering_vigour = models.CharField(max_length=100, blank=True, null=True)
    pest_incidence = models.CharField(max_length=100, blank=True, null=True)
    disease_incidence = models.CharField(max_length=100, blank=True, null=True)
    irrigation_status = models.CharField(max_length=100, blank=True, null=True)
    nutrition_status = models.CharField(max_length=100, blank=True, null=True)
    
    # Field Photos
    field_photo1 = models.ImageField(upload_to='survey_photos/', blank=True, null=True)
    field_photo2 = models.ImageField(upload_to='survey_photos/', blank=True, null=True)
    field_photo3 = models.ImageField(upload_to='survey_photos/', blank=True, null=True)
    
    # Remarks
    remarks = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "survey"

    def save(self, *args, **kwargs):
        if not self.survey_id:
            last_survey = Survey.objects.all().order_by('id').last()
            if last_survey:
                last_id = last_survey.id
                self.survey_id = f"SRV-{last_id + 1:03d}"
            else:
                self.survey_id = "SRV-001"
                
        # Calculate completion percentage
        fields_to_check = [
            self.title, self.officer, self.survey_stage, self.description,
            self.survey_month, self.allocated_dates, self.weed_infestation,
            self.tillering_vigour, self.pest_incidence, self.disease_incidence,
            self.irrigation_status, self.nutrition_status, self.field_photo1,
            self.field_photo2, self.field_photo3, self.remarks
        ]
        
        filled = sum(1 for field in fields_to_check if field)
        total = len(fields_to_check)
        self.completion_percentage = int((filled / total) * 100)
        
        if self.completion_percentage == 100 and self.status != "Completed":
            pass # Or automatically set to completed? Probably better not to overwrite user status.

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.survey_id} - {self.title}"
