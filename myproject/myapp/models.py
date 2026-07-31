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
                
        if not self.officer and self.section_id:
            # Try to assign an officer based on the section
            # Officer.section_ids is a comma separated string
            assigned = False
            for off in Officer.objects.exclude(section_ids__isnull=True).exclude(section_ids=''):
                s_ids = [s.strip() for s in str(off.section_ids).split(',')]
                if str(self.section_id) in s_ids:
                    self.officer = off
                    assigned = True
                    break
            
            # Fallback to division_name matching
            if not assigned and self.division_name:
                for off in Officer.objects.exclude(division_names__isnull=True).exclude(division_names=''):
                    d_names = [d.strip() for d in str(off.division_names).split(',')]
                    if self.division_name in d_names:
                        self.officer = off
                        break

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

    @property
    def get_division_obj(self):
        from .models import Division
        if self.division:
            return Division.objects.filter(code=self.division).first() or Division.objects.filter(name=self.division).first()
        return None

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
    
    group = models.ForeignKey('Group', on_delete=models.SET_NULL, null=True, blank=True)
    group_name = models.CharField(max_length=100, blank=True, null=True)
    factory = models.ForeignKey('Factory', on_delete=models.SET_NULL, null=True, blank=True)
    factory_name = models.CharField(max_length=100, blank=True, null=True)
    plot_name = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "survey"

    def save(self, *args, **kwargs):
        if not self.survey_id:
            from django.db.models import Max
            max_survey = Survey.objects.all().aggregate(Max('id'))
            next_id = (max_survey['id__max'] or 0) + 1
            
            while True:
                candidate_id = f"SRV-{next_id:03d}"
                if not Survey.objects.filter(survey_id=candidate_id).exists():
                    self.survey_id = candidate_id
                    break
                next_id += 1
                
        # Auto-populate denormalized fields from the associated plot
        if self.plot:
            from .models import Group, Factory  # Import here to avoid circular imports if any
            
            if not self.group_id:
                self.group_id = self.plot.group_id
                if not self.group_id and self.officer_id:
                    if Group.objects.filter(id=self.officer.group_id).exists():
                        self.group_id = self.officer.group_id
            if not self.group_name:
                self.group_name = self.plot.group_name
                if not self.group_name and self.officer_id:
                    self.group_name = self.officer.group_name
                    
            if not self.factory_id:
                self.factory_id = self.plot.factory_id
                if not self.factory_id and self.officer_id and self.officer.factory_ids:
                    f_ids = self.officer.factory_ids.replace('[', '').replace(']', '').replace("'", "").replace('"', "")
                    f_ids_list = [x.strip() for x in f_ids.split(',') if x.strip()]
                    if f_ids_list and f_ids_list[0].isdigit():
                        cand_factory_id = int(f_ids_list[0])
                        if Factory.objects.filter(id=cand_factory_id).exists():
                            self.factory_id = cand_factory_id
                            
            if not self.factory_name:
                self.factory_name = self.plot.factory_name
                if not self.factory_name and self.officer_id and self.officer.factory_names:
                    f_names = self.officer.factory_names.replace('[', '').replace(']', '').replace("'", "").replace('"', "")
                    f_names_list = [x.strip() for x in f_names.split(',') if x.strip()]
                    if f_names_list:
                        self.factory_name = f_names_list[0]
                        
            if not self.plot_name:
                self.plot_name = self.plot.plot_code

        super().save(*args, **kwargs)

    @property
    def completion_percentage(self):
        allocated_count = self.number_of_days
        if allocated_count and allocated_count > 0:
            completed_dates = {
                r.survey_date for r in self.results.all()
                if getattr(r, 'survey_status', None) == 'Completed' and getattr(r, 'survey_date', None)
            }
            return min(int((len(completed_dates) / allocated_count) * 100), 100)
        return 0
        
    @property
    def status(self):
        return 'Completed' if self.completion_percentage == 100 else 'Active'

    @property
    def completed_dates_list(self):
        dates = {
            r.survey_date.strftime('%Y-%m-%d') for r in self.results.all()
            if getattr(r, 'survey_status', None) == 'Completed' and getattr(r, 'survey_date', None)
        }
        return list(dates)

    def __str__(self):
        return f"{self.survey_id} - {self.title}"

class SurveyResult(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="results")
    survey_date = models.DateField(blank=True, null=True, help_text="Date when this survey result was taken")
    weed_infestation = models.CharField(max_length=100, blank=True, null=True)
    tillering_vigour = models.CharField(max_length=100, blank=True, null=True)
    pest_incidence = models.CharField(max_length=100, blank=True, null=True)
    disease_incidence = models.CharField(max_length=100, blank=True, null=True)
    irrigation_status = models.CharField(max_length=100, blank=True, null=True)
    nutrition_status = models.CharField(max_length=100, blank=True, null=True)
    
    # Field Photos
    field_photo1 = models.URLField(max_length=1000, blank=True, null=True)
    field_photo2 = models.URLField(max_length=1000, blank=True, null=True)
    field_photo3 = models.URLField(max_length=1000, blank=True, null=True)
    
    # Remarks
    remarks = models.TextField(blank=True, null=True)
    
    # Status
    survey_status = models.CharField(max_length=50, default='Pending')
    completion_percentage = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "survey_result"

    def save(self, *args, **kwargs):
        # Auto-update status if data is present
        if self.weed_infestation or self.tillering_vigour or self.remarks or self.field_photo1:
            self.survey_status = 'Completed'
            
        super().save(*args, **kwargs)
        
        # Calculate completion percentage for the parent survey
        survey = self.survey
        allocated_count = survey.number_of_days
        if allocated_count and allocated_count > 0:
            completed_count = survey.results.filter(survey_status='Completed').values('survey_date').distinct().count()
            perc = min(int((completed_count / allocated_count) * 100), 100)
        else:
            perc = 100
            
        # Update completion_percentage across all SurveyResult rows for this survey
        SurveyResult.objects.filter(survey=survey).update(completion_percentage=perc)

    def __str__(self):
        return f"Result for {self.survey.survey_id}"


class NDVIRecord(models.Model):
    plot = models.ForeignKey(Plot, on_delete=models.CASCADE, related_name="ndvi_records")
    date_recorded = models.DateField()
    ndvi_value = models.DecimalField(max_digits=5, decimal_places=4)
    cloud_cover = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    health_status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # New fields added based on the spreadsheet columns
    crop_age_days = models.IntegerField(null=True, blank=True)
    stage = models.CharField(max_length=100, null=True, blank=True)
    ndvi_mean = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    ndvi_min = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    ndvi_max = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    thr_min = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    thr_max = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    good_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    mod_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    attn_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    px_good = models.IntegerField(null=True, blank=True)
    px_mod = models.IntegerField(null=True, blank=True)
    px_attn = models.IntegerField(null=True, blank=True)
    px_total = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "ndvi_record"
        ordering = ['-date_recorded']

    def __str__(self):
        return f"{self.plot.plot_code} - {self.date_recorded} ({self.ndvi_value})"

class Scout(models.Model):
    scout_id = models.CharField(max_length=50, unique=True, blank=True)
    plot = models.ForeignKey(Plot, on_delete=models.CASCADE, related_name="scouts")
    ndvi_value = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    alert_reason = models.TextField()
    priority = models.CharField(max_length=20, default='Medium')
    status = models.CharField(max_length=50, default='Pending Assignment') 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "scout"

    def save(self, *args, **kwargs):
        if not self.scout_id:
            last_scout = Scout.objects.all().order_by('id').last()
            if last_scout:
                self.scout_id = f"SCT-{last_scout.id + 1:04d}"
            else:
                self.scout_id = "SCT-0001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.scout_id} - {self.plot.plot_code}"

class ScoutAssignment(models.Model):
    scout = models.OneToOneField(Scout, on_delete=models.CASCADE, related_name="assignment")
    officer = models.ForeignKey(Officer, on_delete=models.CASCADE, related_name="assigned_scouts")
    assigned_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "scout_assignment"

class ScoutSurveyReport(models.Model):
    scout = models.OneToOneField(Scout, on_delete=models.CASCADE, related_name="survey_report")
    officer = models.ForeignKey(Officer, on_delete=models.CASCADE, related_name="scout_reports")
    field_photo1 = models.ImageField(upload_to='scout_photos/', blank=True, null=True)
    field_photo2 = models.ImageField(upload_to='scout_photos/', blank=True, null=True)
    observations = models.TextField(blank=True, null=True)
    pest_details = models.TextField(blank=True, null=True)
    disease_details = models.TextField(blank=True, null=True)
    recommendation = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "scout_survey_report"

from django.db.models.signals import post_save
from django.dispatch import receiver

import datetime

STAGE_SURVEY_DAYS = {
    'Germination': [15, 30],
    'Early Tiller': [45, 60, 75],
    'Tillering': [90, 105, 120],
    'Grand growth': [150, 180, 210, 240],
    'Maturity': [255, 270] 
}

@receiver(post_save, sender=Plot)
def create_surveys_on_plot_creation(sender, instance, created, **kwargs):
    """
    Automatically create all surveys for all stages when a plot is created with a planting_date,
    or if planting_date is updated.
    """
    if instance.planting_date:
        officer = None
        if instance.division_id:
            div_id_str = str(instance.division_id)
            for off in Officer.objects.all():
                if off.division_ids:
                    cleaned = off.division_ids.replace('[', '').replace(']', '').replace("'", "").replace('"', "")
                    ids = [x.strip() for x in cleaned.split(',') if x.strip()]
                    if div_id_str in ids:
                        officer = off
                        break
        
        for stage, survey_days in STAGE_SURVEY_DAYS.items():
            if not survey_days:
                continue
                
            survey_exists = Survey.objects.filter(plot=instance, survey_stage=stage).exists()
            if not survey_exists:
                allocated_dates = []
                base_date = instance.planting_date
                
                # Absolute days from planting_date
                for day_offset in survey_days:
                    calc_date = base_date + datetime.timedelta(days=day_offset)
                    allocated_dates.append(calc_date.strftime('%Y-%m-%d'))
                    
                number_of_days = len(allocated_dates)
                first_date_obj = base_date + datetime.timedelta(days=survey_days[0])
                survey_month = first_date_obj.strftime('%B %Y')
                
                survey = Survey.objects.create(
                    plot=instance,
                    officer=officer,
                    survey_stage=stage,
                    title=f"{stage} Survey for Plot {instance.plot_code}",
                    description=f"Auto-assigned future survey for {stage} stage based on planting date.",
                    number_of_days=number_of_days,
                    allocated_dates=allocated_dates,
                    survey_month=survey_month
                )
                
                for date_str in allocated_dates:
                    survey_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                    SurveyResult.objects.create(
                        survey=survey,
                        survey_date=survey_date,
                        survey_status='Pending'
                    )

@receiver(post_save, sender=NDVIRecord)
def create_scout_on_critical_health(sender, instance, created, **kwargs):
    """
    Automatically create and assign a Scout when NDVIRecord shows 'Critical' or 'Moderate' health status.
    """
    status_val = str(instance.health_status).strip()
    if status_val in ['Critical', 'Need attention', 'Need Attention', 'critical', 'need attention']:
        # Check if there's already an active scout (Pending or Assigned) for this plot
        active_scouts_exist = Scout.objects.filter(
            plot=instance.plot, 
            status__in=['Pending Assignment', 'Assigned']
        ).exists()
        
        if not active_scouts_exist:
            # Determine Priority based on health status
            priority = 'High' if status_val in ['Critical', 'Need attention', 'Need Attention', 'critical', 'need attention'] else 'Medium'
            alert_reason = f"Automated Scout Alert: Plot Health Status dropped to {status_val}."
            
            # Create Scout
            scout = Scout.objects.create(
                plot=instance.plot,
                ndvi_value=instance.ndvi_value,
                alert_reason=alert_reason,
                priority=priority,
                status='Pending Assignment'
            )
            
            # Find the officer assigned to this division
            officer = None
            if instance.plot.division_id:
                div_id_str = str(instance.plot.division_id)
                for off in Officer.objects.all():
                    if off.division_ids:
                        cleaned = off.division_ids.replace('[', '').replace(']', '').replace("'", "").replace('"', "")
                        ids = [x.strip() for x in cleaned.split(',') if x.strip()]
                        if div_id_str in ids:
                            officer = off
                            break
            
            # Create ScoutAssignment if officer found
            if officer:
                ScoutAssignment.objects.create(
                    scout=scout,
                    officer=officer,
                    notes=f"Auto-assigned due to {instance.health_status} health status."
                )
                scout.status = 'Assigned'
                scout.save()

class ScoutResult(models.Model):
    previous_scout_id = models.CharField(max_length=50, blank=True, null=True)
    farmer_name = models.CharField(max_length=150, blank=True, null=True)
    plot_id = models.CharField(max_length=50, blank=True, null=True)
    recommendation_adopted = models.BooleanField(default=False)
    current_problem_status = models.CharField(max_length=255, blank=True, null=True)
    current_crop_status = models.CharField(max_length=255, blank=True, null=True)
    seek_expert_help = models.BooleanField(default=False)
    field_photos = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "scout_result"

    def __str__(self):
        return f"Scout Result - {self.id}"

@receiver(post_save, sender=Officer)
def auto_assign_work_on_officer_save(sender, instance, created, **kwargs):
    if instance.division_ids:
        div_ids_str = str(instance.division_ids).replace('[', '').replace(']', '').replace("'", "").replace('"', "")
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
