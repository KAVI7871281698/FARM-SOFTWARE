import os
import django
import csv
import struct
import binascii

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Plot

def parse_ewkb_point(hex_str):
    try:
        b = binascii.unhexlify(hex_str)
        endian = '<' if b[0] == 1 else '>'
        type_srid = struct.unpack(endian + 'I', b[1:5])[0]
        has_srid = (type_srid & 0x20000000) != 0
        offset = 9 if has_srid else 5
        x, y = struct.unpack(endian + 'dd', b[offset:offset+16])
        return y, x  # lat, lon
    except Exception as e:
        print(f"Error parsing point {hex_str}: {e}")
        return None, None

def parse_ewkb_polygon(hex_str):
    try:
        b = binascii.unhexlify(hex_str)
        endian = '<' if b[0] == 1 else '>'
        type_srid = struct.unpack(endian + 'I', b[1:5])[0]
        has_srid = (type_srid & 0x20000000) != 0
        offset = 9 if has_srid else 5
        
        num_rings = struct.unpack(endian + 'I', b[offset:offset+4])[0]
        offset += 4
        
        # Parse only the exterior ring
        if num_rings > 0:
            num_points = struct.unpack(endian + 'I', b[offset:offset+4])[0]
            offset += 4
            
            points = []
            for _ in range(num_points):
                x, y = struct.unpack(endian + 'dd', b[offset:offset+16])
                offset += 16
                points.append({"pont2": x, "point1": y})
            return points
        return []
    except Exception as e:
        print(f"Error parsing polygon {hex_str}: {e}")
        return []

def run():
    file_path = '007- plots_rows.csv'
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    updated_count = 0
    not_found_count = 0

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            plot_no = row.get('plot_no')
            centroid_hex = row.get('centroid')
            boundary_hex = row.get('boundary')
            gps_area = row.get('gps_area_acres')

            if not plot_no:
                continue

            try:
                plot = Plot.objects.get(plot_code=plot_no)
                
                needs_save = False
                
                # Process centroid -> center_lt_ln
                if centroid_hex:
                    lat, lon = parse_ewkb_point(centroid_hex)
                    if lat and lon:
                        plot.center_lt_ln = [f"{lat}, {lon}"]
                        needs_save = True
                
                # Process boundary -> boundaries
                if boundary_hex:
                    points = parse_ewkb_polygon(boundary_hex)
                    if points:
                        plot.boundaries = points
                        needs_save = True
                        
                # Process GPS Area
                if gps_area:
                    try:
                        plot.gps_area = float(gps_area)
                        needs_save = True
                    except ValueError:
                        pass
                        
                if needs_save:
                    plot.save()
                    updated_count += 1
                    
            except Plot.DoesNotExist:
                not_found_count += 1
                
    print(f"Finished processing. Successfully updated: {updated_count} plots.")
    print(f"Plots from CSV not found in DB: {not_found_count} plots.")

if __name__ == '__main__':
    run()
