import re

def insert_import_form(filepath, form_url_name, button_text_to_match):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Form to insert
    form_html = f"""
        <div style="display: flex; gap: 10px;">
            <form action="{{% url '{form_url_name}' %}}" method="post" enctype="multipart/form-data" style="display: flex; gap: 10px; align-items: center;">
                {{% csrf_token %}}
                <input type="file" name="excel_file" accept=".xlsx, .xls, .csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel, text/csv" required style="padding: 0.4rem; border-radius: 6px; border: 1px solid #ccc; font-family: 'Outfit'; font-size: 14px;">
                <button type="submit" style="background: #28a745; color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 8px; font-weight: 600; cursor: pointer; font-family: 'Outfit';"><i class="fa-solid fa-file-import"></i> Import</button>
            </form>
"""
    
    # Find the button
    # e.g., <button onclick="window.location.href='{% url 'add_division' %}'"
    pattern = r"(<button\s+onclick=\"window\.location\.href='\{%\s*url\s+'" + button_text_to_match + r"'\s*%\}'\"[^>]*>[\s\S]*?</button>)"
    
    match = re.search(pattern, content)
    if match:
        original_button = match.group(1)
        # Check if already wrapped in a flex div with gap: 10px
        # We can just replace the button with the wrapper and button and closing div.
        replacement = form_html + "            " + original_button + "\n        </div>"
        
        # Prevent double injection
        if "fa-file-import" not in content:
            new_content = content[:match.start()] + replacement + content[match.end():]
            with open(filepath, 'w') as f:
                f.write(new_content)
            print(f"Updated {filepath}")
        else:
            print(f"Already updated {filepath}")
    else:
        print(f"Button not found in {filepath}")

# users.html
insert_import_form(r"d:\Own Apps\Clients docs\Farm Signals\myproject\myapp\templates\users.html", "import_farmers", "add_farmer")
