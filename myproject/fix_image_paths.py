import os, re
d = 'myapp/templates'
for f in os.listdir(d):
    if f.endswith('.html'):
        path = os.path.join(d, f)
        with open(path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Replace the hardcoded C:/ path with django static tag
        new_content = re.sub(r'C:/Users/[^"\'\>]*?\.png', r"{% static 'images/real_bg.png' %}", content)
        
        # We also need to ensure {% load static %} is at the top of the file
        if '{% static ' in new_content and '{% load static %}' not in new_content:
            new_content = '{% load static %}\n' + new_content
            
        with open(path, 'w', encoding='utf-8') as file:
            file.write(new_content)
