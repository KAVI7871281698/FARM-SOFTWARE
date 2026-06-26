import os
path = r'd:\Own Apps\Clients docs\Farm Signals\myproject\myapp\models.py'
with open(path, 'a', encoding='utf-8') as f:
    f.write('''

class NDVIRecord(models.Model):
    plot = models.ForeignKey(Plot, on_delete=models.CASCADE, related_name="ndvi_records")
    date_recorded = models.DateField()
    ndvi_value = models.DecimalField(max_digits=5, decimal_places=4)
    cloud_cover = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    health_status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ndvi_record"

    def __str__(self):
        return f"{self.plot.plot_code} - {self.date_recorded} - {self.ndvi_value}"

class ScoutAlert(models.Model):
    scout_id = models.CharField(max_length=50, unique=True, blank=True)
    plot = models.ForeignKey(Plot, on_delete=models.CASCADE, related_name="scout_alerts")
    ndvi_value = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    alert_reason = models.TextField()
    priority = models.CharField(max_length=20)
    status = models.CharField(max_length=50, default="Pending Assignment")
    assigned_officer = models.ForeignKey(Officer, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_scouts")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "scout_alert"

    def save(self, *args, **kwargs):
        if not self.scout_id:
            last_scout = ScoutAlert.objects.all().order_by('id').last()
            if last_scout:
                last_id = last_scout.id
                self.scout_id = f"SCT-{last_id + 1:04d}"
            else:
                self.scout_id = "SCT-0001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.scout_id} - {self.plot.plot_code}"

class ScoutSurveyReport(models.Model):
    scout = models.OneToOneField(ScoutAlert, on_delete=models.CASCADE, related_name="survey_report")
    officer = models.ForeignKey(Officer, on_delete=models.SET_NULL, null=True, blank=True)
    field_photo1 = models.URLField(max_length=1000, blank=True, null=True)
    field_photo2 = models.URLField(max_length=1000, blank=True, null=True)
    observations = models.TextField(blank=True, null=True)
    pest_details = models.TextField(blank=True, null=True)
    disease_details = models.TextField(blank=True, null=True)
    recommendation = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "scout_survey_report"

    def __str__(self):
        return f"Report for {self.scout.scout_id}"
''')
