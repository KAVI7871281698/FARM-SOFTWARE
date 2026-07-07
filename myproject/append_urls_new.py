with open("myapp/urls.py", "a") as f:
    f.write('''
path('import_divisions/', views.import_divisions, name='import_divisions'),
path('import_sections/', views.import_sections, name='import_sections'),
path('import_villages/', views.import_villages, name='import_villages'),
path('import_farmers/', views.import_farmers, name='import_farmers'),
''')
