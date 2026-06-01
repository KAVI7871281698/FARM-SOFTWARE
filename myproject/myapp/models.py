from django.db import models

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Officer(models.Model):
    user_id = models.CharField(max_length=50, null=True, blank=True)
    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100, unique=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True)
    permissions = models.JSONField(default=list, blank=True, null=True)

    def save(self, *args, **kwargs):
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
