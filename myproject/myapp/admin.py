from django.contrib import admin
from .models import Role, Officer, Variety, Group, Factory

admin.site.register(Role)
admin.site.register(Officer)

admin.site.register(Variety)
admin.site.register(Group)
admin.site.register(Factory)
