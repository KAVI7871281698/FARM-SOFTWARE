import os
import re

template_dir = r"d:\Own Apps\Clients docs\Farm Signals\myproject\myapp\templates"
skip_files = ['index.html', 'signup.html', 'forgot-password.html', 'base.html']

for filename in os.listdir(template_dir):
    if not filename.endswith('.html') or filename in skip_files:
        continue
    
    filepath = os.path.join(template_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # If already extends base, skip
    if "{% extends 'base.html' %}" in content:
        continue

    # Extract title
    title_match = re.search(r'<title>Farm Signals - (.*?)</title>', content)
    title = title_match.group(1) if title_match else "Page"
    
    # Check if header exists
    header_end = content.find('</header>')
    if header_end == -1:
        print(f"Skipping {filename} - no </header> found")
        continue
    
    header_end += len('</header>')
    main_end = content.rfind('</main>')
    
    core_content = content[header_end:main_end].strip()

    # Extract scripts (everything between </main> and </body>)
    body_end = content.rfind('</body>')
    scripts = content[main_end + len('</main>'):body_end].strip()
    
    new_html = f"""{{% extends 'base.html' %}}

{{% block title %}}{title}{{% endblock %}}
{{% block header_title %}}{title}{{% endblock %}}

{{% block content %}}
{core_content}
{{% endblock %}}

{{% block scripts %}}
{scripts}
{{% endblock %}}
"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_html)
    print(f"Refactored {filename}")
