import os
import django
from django.test import RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from myapp.views import api_add_plot
from myapp.models import Plot

# Set up test data
plot = Plot.objects.filter(id=5).first()
if plot:
    plot.boundary_image = []
    plot.save()
    
    factory = RequestFactory()
    
    file_data = b'test image content'
    test_file = SimpleUploadedFile("test_boundary.jpg", file_data, content_type="image/jpeg")
    
    data = {
        "plot_id": 5,
        "officer_id": plot.officer.id if plot.officer else 22,
        "farmer_name": plot.farmer.id if plot.farmer else 4,
        "boundary_image": test_file
    }
    
    request = factory.post('/api/add_plot/', data=data)
    response = api_add_plot(request)
    
    import json
    res_data = json.loads(response.content.decode('utf-8'))
    print("API Response boundary_image:", res_data.get('data', {}).get('boundary_image'))
    print("API Response debug_files_keys:", res_data.get('data', {}).get('debug_files_keys'))
