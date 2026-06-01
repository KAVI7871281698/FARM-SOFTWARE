import os, re
d = 'myapp/templates'
for f in os.listdir(d):
    if f.endswith('.html'):
        path = os.path.join(d, f)
        with open(path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Replace the wrong static path with the correct one
        new_content = content.replace("{% static 'images/real_bg.png' %}", "{% static 'real_bg.png' %}")
        
        with open(path, 'w', encoding='utf-8') as file:
            file.write(new_content)
