import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Plot

missing_codes = ['8000799244', 'PLT-0009', '8000801552', '8000787509', '8000789556', 'PLT-0007', '8000788077', 'PLT-0006', '8000788078', '8000789223']
plots = Plot.objects.filter(plot_code__in=missing_codes)
for p in plots:
    print(f"Plot: {p.plot_code}, Status: {p.status}")
