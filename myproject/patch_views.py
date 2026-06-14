import re

path = 'myapp/views.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'return public_url',
    'return public_url, None'
)
content = content.replace(
    'return None',
    'return None, str(e)'
)

# Update api_add_plot
# 1) Add debug_files and supabase_errors to the uploaded_urls loop
pattern1 = r"(uploaded_urls = \[\]\s+)for key in request\.FILES\.keys\(\):"
repl1 = r"\1debug_files = list(request.FILES.keys())\n                supabase_errors = []\n                for key in request.FILES.keys():"
content = re.sub(pattern1, repl1, content, count=1)

# 2) Patch the supabase_url try/except
pattern2 = r"(supabase_url = upload_file_to_supabase\(file, file\.name\)\s+)if supabase_url:\s+uploaded_urls\.append\(supabase_url\)\s+else:\s+filename = default_storage\.save\(f\"plot_boundaries/\{file\.name\}\", file\)\s+uploaded_urls\.append\(default_storage\.url\(filename\)\)\s+except OSError:"
repl2 = r"supabase_url, sb_err = upload_file_to_supabase(file, file.name)\n                                if supabase_url:\n                                    uploaded_urls.append(supabase_url)\n                                else:\n                                    if sb_err: supabase_errors.append(sb_err)\n                                    filename = default_storage.save(f\"plot_boundaries/{file.name}\", file)\n                                    uploaded_urls.append(default_storage.url(filename))\n                            except OSError as e:\n                                supabase_errors.append(f\"Fallback local storage failed: {str(e)}\")"
content = re.sub(pattern2, repl2, content, count=1)

# 3) Add debug variables to JSON response in update
pattern3 = r"('boundaries': plot\.boundaries)\n\s+\}"
repl3 = r"\1,\n                'debug_files_keys': debug_files,\n                'debug_supabase_errors': supabase_errors\n            }"
content = re.sub(pattern3, repl3, content, count=1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched views.py")
