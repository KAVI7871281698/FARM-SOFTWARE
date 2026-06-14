import os
import django
from django.test import RequestFactory

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from myapp.views import api_add_plot
from myapp.models import Plot

factory = RequestFactory()

# We will send the exact same data to see the exact response
data = {
    "plot_id": 6,
    "officer_id": 22,
    "farmer_name": 4,
    "boundaries": '[{"point1": 11.0168, "pont2": 76.955899}]'
}

request = factory.post('/api/add_plot/', data=data)
response = api_add_plot(request)

import json
print("Status code:", response.status_code)
print("Response content:", response.content.decode('utf-8'))
