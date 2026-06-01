import json
import re
import os

log_path = r"C:\Users\chiya\.gemini\antigravity-ide\brain\cc41156c-9863-4dda-b277-76d94d2d983e\.system_generated\logs\transcript.jsonl"
out_dir = r"d:\Own Apps\Clients docs\myproject\myapp\templates\recovered"
os.makedirs(out_dir, exist_ok=True)

files_recovered = {}

with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            content = data.get('content', '')
            
            # Check for replace_file_content or write_to_file or VIEW_FILE outputs that contain the file contents
            if '<!DOCTYPE html>' in content:
                # This could be a full file dump
                # Let's just find anything between <style> and </style>
                styles = re.findall(r'<style>(.*?)</style>', content, re.DOTALL)
                if styles:
                    # Let's save all styles found
                    for i, s in enumerate(styles):
                        with open(os.path.join(out_dir, f"style_{data.get('step_index')}_{i}.css"), 'w', encoding='utf-8') as sf:
                            sf.write(s)
        except Exception as e:
            pass
