from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Role, Officer, Section, Village, Farmer, Variety, Crop, Group, Factory, Division, WorkAssign, Plot, SoilType, ScoutingLog, Survey, SurveyResult
import json

def parse_legacy_field(val):
    if not val: return []
    val = str(val).strip()
    if val.startswith('[') and val.endswith(']'):
        try:
            val = val.replace("'", '"')
            return [str(x) for x in json.loads(val)]
        except:
            pass
    return [x.strip() for x in val.split(',')] if val else []

def format_boundaries_list(boundaries_data):
    if not isinstance(boundaries_data, list):
        return boundaries_data
    formatted = []
    for b in boundaries_data:
        if isinstance(b, dict):
            lat = b.get('lat', b.get('point1'))
            lng = b.get('lng', b.get('point2', b.get('pont2')))
            if lat is not None and lng is not None:
                formatted.append({"point1": lat, "point2": lng})
            else:
                formatted.append(b)
        else:
            formatted.append(b)
    return formatted

def extract_boundaries_from_request(request):
    boundaries_list = []
    for k in request.POST.keys():
        k_lower = k.lower()
        if 'boundar' in k_lower:
            if 'image' in k_lower:
                continue
            for val in request.POST.getlist(k):
                boundaries_list.append(val)
    if not boundaries_list: return None
    b_data = []
    for val in boundaries_list:
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list): b_data.extend(parsed)
            else: b_data.append(parsed)
        except:
            b_data.append(val)
    return b_data

def extract_boundary_image_from_request(request):
    img_list = []
    for k in request.POST.keys():
        if 'boundary_image' in k.lower():
            for val in request.POST.getlist(k):
                if str(val).strip():
                    img_list.append(val)
    parsed_imgs = []
    for val in img_list:
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list): parsed_imgs.extend(parsed)
            else:
                if parsed: parsed_imgs.append(parsed)
        except:
            if val: parsed_imgs.append(val)
    return parsed_imgs

def upload_file_to_supabase(file_obj, original_filename):
    import os
    import uuid
    from supabase import create_client, Client
    url = os.environ.get("SUPABASE_URL")
    if url and url.endswith('/rest/v1/'): url = url[:-9]
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key: return None, "Supabase URL or Key missing in environment"
    try:
        supabase: Client = create_client(url, key)
        file_bytes = file_obj.read()
        file_obj.seek(0)
        ext = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        res = supabase.storage.from_('plot_boundaries').upload(
            file=file_bytes,
            path=unique_filename,
            file_options={"content-type": getattr(file_obj, 'content_type', 'application/octet-stream')}
        )
        return supabase.storage.from_('plot_boundaries').get_public_url(unique_filename), None
    except Exception as e:
        return None, str(e)

def mobile_index_handler(request):
    keys = request.POST.keys()
    
    if 'farmer_name' in keys and 'officer_id' in keys:
        return api_add_plot(request)
    elif 'survey_id' in keys and 'weed_infestation' in keys:
        return api_update_survey(request)
    elif 'user_id' in keys and 'password' in keys:
        is_mobile = 'device_id' in keys or 'lt' in keys or 'ln' in keys
        if is_mobile:
            user_id = request.POST.get('user_id')
            password = request.POST.get('password')
            user = Officer.objects.filter(user_id=user_id, password=password).first()
            if user:
                device_id = request.POST.get('device_id')
                lt = request.POST.get('lt')
                ln = request.POST.get('ln')
                if device_id: user.device_id = device_id
                if lt: user.latitude = lt
                if ln: user.longitude = ln
                user.save()
                return JsonResponse({
                    'status': 'success',
                    'message': 'Login successful',
                    'data': {
                        'id': user.id,
                        'user_id': user.user_id,
                        'name': user.name,
                        'mobile': user.mobile,
                        'email': user.email,
                        'role_name': user.role.name if user.role else None,
                        'permissions': user.permissions or [],
                        'device_id': user.device_id,
                        'latitude': user.latitude,
                        'longitude': user.longitude,
                        'group_name': user.group_name
                    }
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid User ID or password.'}, status=401)
    elif 'officer_id' in keys and 'device_id' in keys and 'plot_action' not in keys and 'get_farmers' not in keys and 'crop_id' not in keys:
        officer_id = request.POST.get('officer_id')
        device_id = request.POST.get('device_id')
        lt = request.POST.get('lt')
        ln = request.POST.get('ln')
        survey_view = request.POST.get('survey_view')
        if str(survey_view).lower() == 'true':
            surveys = Survey.objects.filter(officer__user_id=officer_id) | Survey.objects.filter(officer_id=officer_id)
            surveys = surveys.distinct().order_by('-id')
            surveys_data = []
            for s in surveys:
                surveys_data.append({
                    'survey_id': s.survey_id,
                    'title': s.title or '-',
                    'plot_code': s.plot.plot_code if s.plot else '-',
                    'farmer_name': s.plot.farmer.name if s.plot and s.plot.farmer else '-',
                    'survey_stage': s.survey_stage or '-',
                    'survey_month': s.survey_month or '-',
                    'number_of_days': s.number_of_days,
                    'allocated_dates': s.allocated_dates or [],
                    'status': s.status,
                    'completion_percentage': s.completion_percentage,
                    'description': s.description or '-'
                })
            return JsonResponse({'status': 'success', 'message': 'Surveys fetched successfully', 'data': surveys_data})
        work_assigns = WorkAssign.objects.filter(officer_id=officer_id)
        update_fields = {}
        if device_id: update_fields['device_id'] = device_id
        if lt: update_fields['latitude'] = lt
        if ln: update_fields['longitude'] = ln
        if update_fields:
            work_assigns.update(**update_fields)
        data = []
        for wa in work_assigns:
            village_plots = []
            if wa.village:
                plots = Plot.objects.filter(village=wa.village)
                for p in plots:
                    village_plots.append({
                        'id': p.id, 'plot_code': p.plot_code, 'farmer_name': p.farmer.name if p.farmer else None,
                        'farmer_phone': p.farmer.phone if p.farmer else None, 'crop_name': p.crop_type.crop_name if p.crop_type else None,
                        'variety_name': p.variety.variety_name if p.variety else None, 'area_acre': str(p.area_acre) if p.area_acre is not None else None,
                        'status': p.status, 'soil_name': p.soil_type.soil_name if p.soil_type else None,
                        'latitude': p.latitude, 'longitude': p.longitude, 'date_planted': str(p.planting_date) if p.planting_date else None,
                    })
            data.append({
                'id': wa.id, 'work_assign_code': wa.work_assign_code, 'division': wa.division,
                'section_id': wa.section.id if wa.section else None, 'section_name': wa.section.section_name if wa.section else None,
                'village_id': wa.village.id if wa.village else None, 'village_name': wa.village.village_name if wa.village else None,
                'status': wa.status, 'plots': village_plots
            })
        return JsonResponse({'status': 'success', 'message': 'Work assigns fetched successfully', 'data': data})
    elif request.POST.get('get_farmers', '').lower() == 'true':
        group_id = request.POST.get('group_id')
        farmers = Farmer.objects.filter(group_id=group_id) if group_id else Farmer.objects.all()
        data = []
        for f in farmers:
            village_name = f.village.village_name if f.village else "No Village"
            display_name = f"{f.name} - {village_name}"
            data.append({'id': f.id, 'farmer_code': f.farmer_code, 'farmer_name': display_name})
        return JsonResponse({'status': 'success', 'message': 'Farmers fetched successfully', 'data': data})
    elif 'crop_id' in keys and 'group_id' in keys and 'device_id' in keys:
        crop_id = request.POST.get('crop_id')
        varieties = Variety.objects.filter(crop_type_id=crop_id)
        data = [{'id': v.id, 'variety_code': v.variety_code, 'variety_name': v.variety_name} for v in varieties]
        return JsonResponse({'status': 'success', 'message': 'Varieties fetched successfully', 'data': data})
    elif 'group_id' in keys and 'device_id' in keys and 'officer_id' not in keys:
        crops = Crop.objects.all()
        data = [{'id': c.id, 'crop_code': c.crop_code, 'crop_name': c.crop_name} for c in crops]
        return JsonResponse({'status': 'success', 'message': 'Crops fetched successfully', 'data': data})
    elif request.POST.get('plot_action', '').lower() == 'true':
        return api_get_plots(request)
    elif request.POST.get('get_soil_types', '').lower() == 'true' and 'device_id' in keys:
        soil_types = SoilType.objects.all()
        data = [{'id': s.id, 'soil_code': s.soil_code, 'soil_name': s.soil_name} for s in soil_types]
        return JsonResponse({'status': 'success', 'message': 'Soil types fetched successfully', 'data': data})
    elif request.POST.get('add_scouting_log', '').lower() == 'true':
        plot_id = request.POST.get('plot_id')
        officer_id = request.POST.get('officer_id')
        try:
            plot = Plot.objects.get(id=plot_id)
            officer = Officer.objects.filter(id=officer_id).first() if officer_id else None
            scout_log = ScoutingLog.objects.create(
                group=plot.group, group_name=plot.group_name, factory=plot.factory,
                division=plot.division, section=plot.section, village=plot.village,
                plot=plot, officer=officer, plant_height=request.POST.get('plant_height'),
                growth_stage=request.POST.get('growth_stage'), pest_presence=request.POST.get('pest_presence', '').lower() in ['true', '1', 'yes'],
                pest_type=request.POST.get('pest_type'), pest_severity=request.POST.get('pest_severity'),
                disease_presence=request.POST.get('disease_presence', '').lower() in ['true', '1', 'yes'],
                disease_type=request.POST.get('disease_type'), disease_photo=request.FILES.get('disease_photo'),
                water_sufficiency=request.POST.get('water_sufficiency'),
                water_stress_symptoms=request.POST.get('water_stress_symptoms', '').lower() in ['true', '1', 'yes'],
                nutrient_deficiency=request.POST.get('nutrient_deficiency', '').lower() in ['true', '1', 'yes'],
                deficiency_symptoms=request.POST.get('deficiency_symptoms'), fertilizer_recommendation=request.POST.get('fertilizer_recommendation')
            )
            return JsonResponse({
                'status': 'success', 'message': 'Scouting log added successfully',
                'data': {
                    'log_id': scout_log.id, 'plot_id': scout_log.plot.id if scout_log.plot else None,
                    'plot_code': scout_log.plot.plot_code if scout_log.plot else None,
                    'officer_id': scout_log.officer.id if scout_log.officer else None,
                    'plant_height': scout_log.plant_height, 'growth_stage': scout_log.growth_stage,
                    'pest_presence': scout_log.pest_presence, 'pest_type': scout_log.pest_type,
                    'pest_severity': scout_log.pest_severity, 'disease_presence': scout_log.disease_presence,
                    'disease_type': scout_log.disease_type, 'disease_photo_url': scout_log.disease_photo.url if scout_log.disease_photo else None,
                    'water_sufficiency': scout_log.water_sufficiency, 'water_stress_symptoms': scout_log.water_stress_symptoms,
                    'nutrient_deficiency': scout_log.nutrient_deficiency, 'deficiency_symptoms': scout_log.deficiency_symptoms,
                    'fertilizer_recommendation': scout_log.fertilizer_recommendation, 'created_at': scout_log.created_at.isoformat() if scout_log.created_at else None
                }
            })
        except Plot.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Plot not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'status': 'error', 'message': 'Unknown API request parameters'}, status=400)
        
    return None

@csrf_exempt
def mobile_api(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'login':
            user_id = request.POST.get('user_id')
            password = request.POST.get('password')
            lt = request.POST.get('lt')
            ln = request.POST.get('ln')
            device_id = request.POST.get('device_id')
            
            user = Officer.objects.filter(user_id=user_id, password=password).first()
            if user:
                return JsonResponse({
                    'status': 'success',
                    'message': 'Login successful',
                    'data': {
                        'id': user.id,
                        'user_id': user.user_id,
                        'name': user.name,
                        'mobile': user.mobile,
                        'email': user.email,
                        'role_name': user.role.name if user.role else None,
                        'group_id': user.group_id if user.group else None,
                        'permissions': user.permissions or [],
                        'device_id': device_id,
                        'latitude': lt,
                        'longitude': ln
                    }
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid User ID or password.'}, status=401)
                
        # Add other actions here, e.g. elif action == 'get_dashboard':
        
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid or missing action parameter'}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)

@csrf_exempt
def mobile_get_work_assigns(request):
    if request.method == 'POST':
        officer_id = request.POST.get('officer_id')
        lt = request.POST.get('lt')
        ln = request.POST.get('ln')
        device_id = request.POST.get('device_id')
        survey_view = request.POST.get('survey_view')
        
        if not officer_id:
            return JsonResponse({'status': 'error', 'message': 'officer_id is required'}, status=400)
            
        work_assigns = WorkAssign.objects.filter(officer_id=officer_id)
        data = []
        for wa in work_assigns:
            data.append({
                'id': wa.id,
                'work_assign_code': wa.work_assign_code,
                'division': wa.division,
                'section_id': wa.section.id if wa.section else None,
                'section_name': wa.section.section_name if wa.section else None,
                'village_id': wa.village.id if wa.village else None,
                'village_name': wa.village.village_name if wa.village else None,
                'status': wa.status,
                'created_at': wa.created_at.strftime('%Y-%m-%d %H:%M:%S') if wa.created_at else None
            })
        
        response_dict = {
            'status': 'success',
            'message': 'Work assigns fetched successfully',
            'data': data
        }
        
        if str(survey_view).lower() == 'true':
            surveys = Survey.objects.filter(officer__user_id=officer_id) | Survey.objects.filter(officer_id=officer_id)
            surveys = surveys.distinct().order_by('-id')
            surveys_data = []
            for s in surveys:
                surveys_data.append({
                    'survey_id': s.survey_id,
                    'title': s.title or '-',
                    'plot_code': s.plot.plot_code if s.plot else '-',
                    'farmer_name': s.plot.farmer.name if s.plot and s.plot.farmer else '-',
                    'survey_stage': s.survey_stage or '-',
                    'survey_month': s.survey_month or '-',
                    'number_of_days': s.number_of_days,
                    'allocated_dates': s.allocated_dates or [],
                    'status': s.status,
                    'completion_percentage': s.completion_percentage,
                    'description': s.description or '-'
                })
            response_dict['survey_data'] = surveys_data
            
        return JsonResponse(response_dict)
        
    return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)

@csrf_exempt
def api_get_varieties(request):
    crop_id = request.POST.get('crop_id') or request.GET.get('crop_id')
    if crop_id:
        varieties = Variety.objects.filter(crop_id=crop_id)
    else:
        varieties = Variety.objects.all()
    
    data = []
    for v in varieties:
        data.append({
            'id': v.id,
            'variety_name': v.variety_name,
            'crop_id': v.crop_id,
        })
    return JsonResponse({'status': 'success', 'data': data})

@csrf_exempt
def api_get_farmers(request):
    get_farmers = request.POST.get('get_farmers') or request.GET.get('get_farmers')
    if str(get_farmers).lower() != 'true':
        return JsonResponse({'status': 'error', 'message': 'get_farmers parameter must be true'}, status=400)
        
    group_id = request.POST.get('group_id') or request.GET.get('group_id')
    lt = request.POST.get('lt') or request.GET.get('lt')
    ln = request.POST.get('ln') or request.GET.get('ln')
    device_id = request.POST.get('device_id') or request.GET.get('device_id')
    
    if group_id:
        farmers = Farmer.objects.filter(group_id=group_id)
    else:
        farmers = Farmer.objects.all()
        
    data = []
    for f in farmers:
        village_name = f.village.village_name if f.village else ''
        display_name = f"{f.name} - {village_name}" if village_name else f.name
        data.append({
            'id': f.id,
            'name': display_name
        })
        
    return JsonResponse({'status': 'success', 'data': data})

@csrf_exempt
def api_add_plot(request):
    if request.method == 'POST':
        plot_id = request.POST.get('plot_id')
        farmer_input = request.POST.get('farmer_name')
        officer_id = request.POST.get('officer_id')

        plot = None
        if plot_id:
            plot = Plot.objects.filter(id=plot_id).first()
            if not plot:
                return JsonResponse({"status": "error", "message": "Plot not found"}, status=404)

        if not plot and (not farmer_input or not officer_id):
            return JsonResponse({"status": "error", "message": "farmer_name and officer_id are required"}, status=400)

        try:
            farmer = None
            if farmer_input:
                try:
                    farmer = Farmer.objects.filter(id=farmer_input).first()
                except ValueError:
                    farmer = Farmer.objects.filter(name=farmer_input).first()
                if not farmer and not plot:
                    return JsonResponse({"status": "error", "message": "Farmer not found"}, status=404)

            officer = Officer.objects.filter(id=officer_id).first() if officer_id else None
            
            crop_id = request.POST.get('crop_id')
            crop = Crop.objects.filter(id=crop_id).first() if crop_id else None
            
            variety_id = request.POST.get('variety_id')
            variety = Variety.objects.filter(id=variety_id).first() if variety_id else None
            
            soil_type_id = request.POST.get('soil_type_id')
            soil_type = SoilType.objects.filter(id=soil_type_id).first() if soil_type_id else None

            if plot:
                # Update existing plot
                if farmer:
                    plot.farmer = farmer
                    division = farmer.section.division if farmer.section and farmer.section.division else None
                    plot.division = division
                    plot.division_name = division.name if division else None
                    plot.section = farmer.section if farmer.section else None
                    plot.section_name = farmer.section.section_name if farmer.section else None
                    plot.village = farmer.village if farmer.village else None
                    plot.village_name = farmer.village.village_name if farmer.village else None
                    plot.group = farmer.group
                    plot.group_name = farmer.group_name
                    plot.factory = farmer.factory
                    plot.factory_name = farmer.factory_name
                    
                if crop: plot.crop_type = crop
                if variety: plot.variety = variety
                if soil_type: plot.soil_type = soil_type
                if officer: plot.officer = officer

                if 'area_acre' in request.POST:
                    area_acre = request.POST.get('area_acre')
                    plot.area_acre = area_acre if area_acre and str(area_acre).strip() != '' else None
                if 'planting_date' in request.POST:
                    planting_date = request.POST.get('planting_date')
                    plot.planting_date = planting_date if planting_date and str(planting_date).strip() != '' else None
                if 'status' in request.POST:
                    plot.status = request.POST.get('status')
                if 'lt' in request.POST:
                    lt_val = request.POST.get('lt')
                    try:
                        import json
                        plot.latitude = json.loads(lt_val) if lt_val else []
                    except:
                        plot.latitude = [lt_val] if lt_val else []
                if 'ln' in request.POST:
                    ln_val = request.POST.get('ln')
                    try:
                        import json
                        plot.longitude = json.loads(ln_val) if ln_val else []
                    except:
                        plot.longitude = [ln_val] if ln_val else []
                if 'center_lt_ln' in request.POST:
                    c_val = request.POST.get('center_lt_ln')
                    try:
                        import json
                        plot.center_lt_ln = json.loads(c_val) if c_val else []
                    except:
                        plot.center_lt_ln = [c_val] if c_val else []
                if 'device_id' in request.POST: plot.device_id = request.POST.get('device_id')
                if 'gps_area' in request.POST:
                    gps_area = request.POST.get('gps_area')
                    plot.gps_area = gps_area if gps_area and str(gps_area).strip() != '' else None
                if 'planting_season' in request.POST: plot.planting_season = request.POST.get('planting_season')
                if 'crushing_season' in request.POST: plot.crushing_season = request.POST.get('crushing_season')
                if 'plot_type' in request.POST: plot.plot_type = request.POST.get('plot_type')
                if 'irrigation_type' in request.POST: plot.irrigation_type = request.POST.get('irrigation_type')
                if 'water_source' in request.POST: plot.water_source = request.POST.get('water_source')
                if 'seed_type' in request.POST: plot.seed_type = request.POST.get('seed_type')
                if 'spacing_ft' in request.POST:
                    spacing_ft = request.POST.get('spacing_ft')
                    plot.spacing_ft = spacing_ft if spacing_ft and str(spacing_ft).strip() != '' else None
                if 'harvest_date' in request.POST:
                    harvest_date = request.POST.get('harvest_date')
                    plot.harvest_date = harvest_date if harvest_date and str(harvest_date).strip() != '' else None
                if 'production_t' in request.POST:
                    production_t = request.POST.get('production_t')
                    plot.production_t = production_t if production_t and str(production_t).strip() != '' else None
                if 'yield_ton_acre' in request.POST:
                    yield_ton_acre = request.POST.get('yield_ton_acre')
                    plot.yield_ton_acre = yield_ton_acre if yield_ton_acre and str(yield_ton_acre).strip() != '' else None
                
                if 'boundary_image' in request.POST:
                    extracted_imgs = extract_boundary_image_from_request(request)
                    if extracted_imgs:
                        plot.boundary_image = extracted_imgs
                    else:
                        plot.boundary_image = []
                
                from django.core.files.storage import default_storage
                uploaded_urls = []
                debug_files = list(request.FILES.keys())
                supabase_errors = []
                for key in request.FILES.keys():
                    if 'boundary_image' in key:
                        for file in request.FILES.getlist(key):
                            try:
                                supabase_url, sb_err = upload_file_to_supabase(file, file.name)
                                if supabase_url:
                                    uploaded_urls.append(supabase_url)
                                else:
                                    if sb_err: supabase_errors.append(sb_err)
                                    filename = default_storage.save(f"plot_boundaries/{file.name}", file)
                                    uploaded_urls.append(default_storage.url(filename))
                            except OSError as err:
                                supabase_errors.append(f"Fallback local storage failed: {str(err)}")
                                # Vercel is read-only, saving files to disk will fail.
                                # Log or ignore the error so it doesn't break the entire plot update
                                pass
                
                if uploaded_urls:
                    if isinstance(plot.boundary_image, list):
                        plot.boundary_image = list(plot.boundary_image) + uploaded_urls
                    else:
                        plot.boundary_image = uploaded_urls
                
                extracted_boundaries = extract_boundaries_from_request(request)
                if extracted_boundaries is not None:
                    plot.boundaries = extracted_boundaries
                else:
                    raw_b = request.POST.get('boundaries')
                    if raw_b:
                        try:
                            import json
                            plot.boundaries = json.loads(raw_b)
                        except:
                            plot.boundaries = [raw_b]
                plot.save()
            else:
                # Create new plot
                area_acre = request.POST.get('area_acre')
                if not area_acre or str(area_acre).strip() == '': area_acre = None
                
                planting_date = request.POST.get('planting_date')
                if not planting_date or str(planting_date).strip() == '': planting_date = None
                
                status = request.POST.get('status', 'Not Mapped')
                lt_val = request.POST.get('lt')
                try:
                    import json
                    lt = json.loads(lt_val) if lt_val else []
                except:
                    lt = [lt_val] if lt_val else []

                ln_val = request.POST.get('ln')
                try:
                    import json
                    ln = json.loads(ln_val) if ln_val else []
                except:
                    ln = [ln_val] if ln_val else []

                c_val = request.POST.get('center_lt_ln')
                try:
                    import json
                    center_lt_ln = json.loads(c_val) if c_val else []
                except:
                    center_lt_ln = [c_val] if c_val else []
                device_id = request.POST.get('device_id')
                gps_area = request.POST.get('gps_area')
                if not gps_area or str(gps_area).strip() == '': gps_area = None
                planting_season = request.POST.get('planting_season')
                crushing_season = request.POST.get('crushing_season')
                plot_type = request.POST.get('plot_type')
                irrigation_type = request.POST.get('irrigation_type')
                water_source = request.POST.get('water_source')
                seed_type = request.POST.get('seed_type')
                spacing_ft = request.POST.get('spacing_ft')
                if not spacing_ft or str(spacing_ft).strip() == '': spacing_ft = None
                harvest_date = request.POST.get('harvest_date')
                if not harvest_date or str(harvest_date).strip() == '': harvest_date = None
                production_t = request.POST.get('production_t')
                if not production_t or str(production_t).strip() == '': production_t = None
                yield_ton_acre = request.POST.get('yield_ton_acre')
                if not yield_ton_acre or str(yield_ton_acre).strip() == '': yield_ton_acre = None

                boundary_image_data = extract_boundary_image_from_request(request)

                from django.core.files.storage import default_storage
                for key in request.FILES.keys():
                    if 'boundary_image' in key:
                        for file in request.FILES.getlist(key):
                            try:
                                supabase_url = upload_file_to_supabase(file, file.name)
                                if supabase_url:
                                    boundary_image_data.append(supabase_url)
                                else:
                                    filename = default_storage.save(f"plot_boundaries/{file.name}", file)
                                    boundary_image_data.append(default_storage.url(filename))
                            except OSError:
                                pass

                extracted_boundaries = extract_boundaries_from_request(request)
                if extracted_boundaries is not None:
                    boundaries_data = extracted_boundaries
                else:
                    boundaries_data = []

                division = farmer.section.division if farmer.section and farmer.section.division else None
                division_name = division.name if division else None
                section = farmer.section if farmer.section else None
                section_name = section.section_name if section else None
                village = farmer.village if farmer.village else None
                village_name = village.village_name if village else None
                group_obj = farmer.group
                group_name = farmer.group_name
                factory_obj = farmer.factory
                factory_name = farmer.factory_name
                
                plot = Plot.objects.create(
                    farmer=farmer,
                    division=division,
                    division_name=division_name,
                    section=section,
                    section_name=section_name,
                    village=village,
                    village_name=village_name,
                    crop_type=crop,
                    variety=variety,
                    planting_date=planting_date,
                    area_acre=area_acre,
                    status=status,
                    soil_type=soil_type,
                    latitude=lt,
                    longitude=ln,
                    center_lt_ln=center_lt_ln,
                    device_id=device_id,
                    gps_area=gps_area,
                    planting_season=planting_season,
                    crushing_season=crushing_season,
                    plot_type=plot_type,
                    irrigation_type=irrigation_type,
                    water_source=water_source,
                    seed_type=seed_type,
                    spacing_ft=spacing_ft,
                    harvest_date=harvest_date,
                    production_t=production_t,
                    yield_ton_acre=yield_ton_acre,
                    group=group_obj,
                    group_name=group_name,
                    factory=factory_obj,
                    factory_name=factory_name,
                    officer=officer,
                    boundary_image=boundary_image_data,
                    boundaries=boundaries_data
                )
        except OSError as err_os:
            if err_os.errno == 30: # Read-only file system (Vercel)
                pass # Just ignore if we can't save on Vercel
            else:
                return JsonResponse({"status": "error", "message": f"File System Error: {str(err_os)}"}, status=400)
        except Exception as err_ex:
            from django.core.exceptions import ValidationError
            import traceback
            error_msg = traceback.format_exc()
            if isinstance(err_ex, ValidationError):
                error_msg = "; ".join(err_ex.messages)
            return JsonResponse({"status": "error", "message": f"Data Validation Error: {error_msg}"}, status=400)

        return JsonResponse({
            "status": "success",
            "message": "Plot added successfully" if not plot_id else "Plot updated successfully",
            "data": {
                "plot_id": plot.id if plot else None,
                "plot_code": plot.plot_code if plot else None,
                "farmer_name": plot.farmer.name if plot and plot.farmer else None,
                "division_name": plot.division_name if plot else None,
                "section_name": plot.section_name if plot else None,
                "village_name": plot.village_name if plot else None,
                "crop_type": plot.crop_type.crop_name if plot and plot.crop_type else None,
                "variety": plot.variety.variety_name if plot and plot.variety else None,
                "planting_date": str(plot.planting_date) if plot and plot.planting_date else None,
                "area_acre": str(plot.area_acre) if plot and plot.area_acre else None,
                "status": plot.status if plot else None,
                "soil_name": plot.soil_type.soil_name if plot and plot.soil_type else None,
                "latitude": plot.latitude if plot else None,
                "longitude": plot.longitude if plot else None,
                "center_lt_ln": plot.center_lt_ln if plot else None,
                "device_id": plot.device_id if plot else None,
                "gps_area": str(plot.gps_area) if plot and plot.gps_area else None,
                "planting_season": plot.planting_season if plot else None,
                "crushing_season": plot.crushing_season if plot else None,
                "plot_type": plot.plot_type if plot else None,
                "irrigation_type": plot.irrigation_type if plot else None,
                "water_source": plot.water_source if plot else None,
                "seed_type": plot.seed_type if plot else None,
                "spacing_ft": str(plot.spacing_ft) if plot and plot.spacing_ft else None,
                "harvest_date": str(plot.harvest_date) if plot and plot.harvest_date else None,
                "production_t": str(plot.production_t) if plot and plot.production_t else None,
                "yield_ton_acre": str(plot.yield_ton_acre) if plot and plot.yield_ton_acre else None,
                "group_name": plot.group_name if plot else None,
                "factory_name": plot.factory_name if plot else None,
                "officer_name": plot.officer.name if plot and plot.officer else None,
                "boundary_image": plot.boundary_image if plot else None,
                "boundaries": plot.boundaries if plot else None,
                "debug_files_keys": debug_files,
                "debug_supabase_errors": supabase_errors
            }
        }, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def api_get_plots(request):
    group_id = request.GET.get('group_id') or request.POST.get('group_id')
    officer_id = request.GET.get('officer_id') or request.POST.get('officer_id')
    lt = request.GET.get('lt') or request.POST.get('lt')
    ln = request.GET.get('ln') or request.POST.get('ln')
    device_id = request.GET.get('device_id') or request.POST.get('device_id')
    plot_action = request.GET.get('plot_action') or request.POST.get('plot_action')
    
    if not group_id or not officer_id:
        return JsonResponse({"status": "error", "message": "group_id and officer_id are required"}, status=400)
        
    if str(plot_action).lower() != 'true':
        return JsonResponse({"status": "error", "message": "plot_action must be 'true' to view plots"}, status=400)
        
    plots = Plot.objects.filter(group_id=group_id, officer_id=officer_id).order_by('-id')
    
    data = []
    for plot in plots:
        data.append({
            "plot_id": plot.id,
            "plot_code": plot.plot_code,
            "farmer_name": plot.farmer.name if plot.farmer else None,
            "division_name": plot.division_name,
            "section_name": plot.section_name,
            "village_name": plot.village_name,
            "crop_type": plot.crop_type.crop_name if plot.crop_type else None,
            "variety": plot.variety.variety_name if plot.variety else None,
            "planting_date": str(plot.planting_date) if plot.planting_date else None,
            "area_acre": str(plot.area_acre) if plot.area_acre else None,
            "status": plot.status,
            "soil_name": plot.soil_type.soil_name if plot.soil_type else None,
            "latitude": plot.latitude,
            "longitude": plot.longitude,
            "center_lt_ln": plot.center_lt_ln,
            "device_id": plot.device_id,
            "group_name": plot.group_name,
            "factory_name": plot.factory_name,
            "officer_name": plot.officer.name if plot.officer else None,
            "boundary_image": plot.boundary_image,
            "boundaries": plot.boundaries
        })
        
    return JsonResponse({
        "status": "success",
        "data": data
    }, status=200)

from .models import FieldMapping

def api_get_farmer_plots(request):
    farmer_id = request.GET.get('farmer_id')
    if farmer_id:
        plots_qs = Plot.objects.filter(farmer_id=farmer_id)
        plots_data = []
        for p in plots_qs:
            plots_data.append({
                'id': p.id,
                'plot_code': p.plot_code,
                'area_acre': str(p.area_acre) if p.area_acre else '0'
            })
        return JsonResponse({'status': 'success', 'plots': plots_data})
    return JsonResponse({'status': 'error', 'message': 'No farmer_id provided'}, status=400)

@csrf_exempt
def api_field_intelligence_plots(request):
    officer_id = request.GET.get('officer_id') or request.POST.get('officer_id')
    lt = request.GET.get('lt') or request.POST.get('lt')
    ln = request.GET.get('ln') or request.POST.get('ln')
    device_id = request.GET.get('device_id') or request.POST.get('device_id')
    field_map = request.GET.get('field_inteliigence_map') or request.POST.get('field_inteliigence_map') or request.GET.get('field_intelligence_map') or request.POST.get('field_intelligence_map')
    
    if str(field_map).lower() != 'true':
        return JsonResponse({"status": "error", "message": "field_inteliigence_map must be 'true'"}, status=400)
    
    if not officer_id:
        return JsonResponse({"status": "error", "message": "officer_id is required"}, status=400)
        
    officer = Officer.objects.filter(id=officer_id).first()
    if not officer:
        return JsonResponse({"status": "error", "message": "Invalid officer_id"}, status=400)
    
    from django.db.models import Q
    import json
    
    base_plots = Plot.objects.filter(
        Q(center_lt_ln__isnull=False) | 
        (Q(latitude__isnull=False) & Q(longitude__isnull=False))
    )
    
    # Filter by factories allowed for the officer
    is_superadmin = (str(officer.role_id) == '1') if getattr(officer, 'role_id', None) else False
    if is_superadmin:
        plots = base_plots
    else:
        fids = [int(x.strip()) for x in str(officer.factory_ids).split(',') if x.strip().isdigit()] if getattr(officer, 'factory_ids', None) else []
        if fids:
            plots = base_plots.filter(farmer__section__division__factory_name_id__in=fids)
        else:
            plots = base_plots.none()
        
    plots_data = []
    for p in plots:
        try:
            lat, lon = None, None
            
            # First try center_lt_ln
            if p.center_lt_ln:
                if isinstance(p.center_lt_ln, list) and len(p.center_lt_ln) >= 2:
                    lat = float(p.center_lt_ln[0])
                    lon = float(p.center_lt_ln[1])
                elif isinstance(p.center_lt_ln, str):
                    try:
                        parsed = json.loads(p.center_lt_ln)
                        if isinstance(parsed, list) and len(parsed) >= 2:
                            lat = float(parsed[0])
                            lon = float(parsed[1])
                    except:
                        pass
            
            # Fallback to latitude/longitude fields
            if lat is None or lon is None:
                lat_str = str(p.latitude).strip("[]'\"")
                lon_str = str(p.longitude).strip("[]'\"")
                if lat_str and lon_str and lat_str != 'None' and lon_str != 'None':
                    lat = float(lat_str)
                    lon = float(lon_str)
            
            if lat is None or lon is None:
                continue
            
            plots_data.append({
                'id': p.id,
                'plot_code': p.plot_code or 'Unknown',
                'lat': lat,
                'lon': lon,
                'division': p.division_name or (p.division.name if p.division else '-'),
                'section': p.section_name or (p.section.section_name if p.section else '-'),
                'village': p.village_name or (p.village.village_name if p.village else '-'),
                'farmer_name': p.farmer.name if p.farmer else '-',
                'planting_date': str(p.planting_date) if p.planting_date else '-',
                'acres': str(p.area_acre) if p.area_acre else '-',
                'soil_type': p.soil_type.soil_name if p.soil_type else '-',
                'status': p.status or '-'
            })
        except (ValueError, TypeError, IndexError):
            continue

    return JsonResponse({
        "status": "success",
        "data": plots_data
    }, status=200)

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def api_surveys(request):
    officer_id = request.GET.get('officer_id') or request.POST.get('officer_id')
    lt = request.GET.get('lt') or request.POST.get('lt')
    ln = request.GET.get('ln') or request.POST.get('ln')
    device_id = request.GET.get('device_id') or request.POST.get('device_id')
    survey_flag = request.GET.get('survey') or request.POST.get('survey') or request.GET.get('servey') or request.POST.get('servey')
    
    if str(survey_flag).lower() != 'true':
        return JsonResponse({"status": "error", "message": "survey param must be 'true'"}, status=400)
    
    if not officer_id:
        return JsonResponse({"status": "error", "message": "officer_id is required"}, status=400)
        
    surveys = Survey.objects.filter(officer__user_id=officer_id) | Survey.objects.filter(officer_id=officer_id)
    surveys = surveys.distinct().order_by('-id')
    
    surveys_data = []
    for s in surveys:
        plot_code = s.plot.plot_code if s.plot else '-'
        farmer_name = s.plot.farmer.name if s.plot and s.plot.farmer else '-'
        
        results_data = []
        for r in s.results.all():
            if r.survey_date:
                results_data.append({
                    "result_id": r.id,
                    "date": r.survey_date.strftime('%Y-%m-%d') if r.survey_date else None,
                    "survey_status": r.survey_status,
                    "completion_percentage": r.completion_percentage
                })

        surveys_data.append({
            'survey_id': s.survey_id,
            'title': s.title or '-',
            'plot_code': plot_code,
            'farmer_name': farmer_name,
            'survey_stage': s.survey_stage or '-',
            'survey_month': s.survey_month or '-',
            'number_of_days': s.number_of_days,
            'allocated_dates': s.allocated_dates or [],
            'description': s.description or '-',
            'survey_results': results_data
        })
        
    return JsonResponse({
        "status": "success",
        "data": surveys_data
    }, status=200)

@csrf_exempt
def api_update_survey(request):
    if request.method == 'POST':
        survey_id = request.POST.get('survey_id')
        if not survey_id:
            return JsonResponse({"status": "error", "message": "survey_id is required"}, status=400)
            
        survey = Survey.objects.filter(survey_id=survey_id).first()
        if not survey:
            return JsonResponse({"status": "error", "message": "Survey not found"}, status=404)
            
        # Get survey_date from POST or default to today
        from datetime import date
        survey_date_str = request.POST.get('survey_date')
        if survey_date_str:
            try:
                from datetime import datetime
                survey_date = datetime.strptime(survey_date_str, '%Y-%m-%d').date()
            except ValueError:
                survey_date = date.today()
        else:
            survey_date = date.today()

        # Create or update SurveyResult for this specific date
        survey_result, created = SurveyResult.objects.get_or_create(survey=survey, survey_date=survey_date)
        
        survey_result.weed_infestation = request.POST.get('weed_infestation', survey_result.weed_infestation)
        survey_result.tillering_vigour = request.POST.get('tillering_vigour', survey_result.tillering_vigour)
        survey_result.pest_incidence = request.POST.get('pest_incidence', survey_result.pest_incidence)
        survey_result.disease_incidence = request.POST.get('disease_incidence', survey_result.disease_incidence)
        survey_result.irrigation_status = request.POST.get('irrigation_status', survey_result.irrigation_status)
        survey_result.nutrition_status = request.POST.get('nutrition_status', survey_result.nutrition_status)
        survey_result.remarks = request.POST.get('remarks', survey_result.remarks)
        
        status_val = request.POST.get('status')
        # status is now a property computed dynamically based on completion_percentage
        
        if request.POST.get('field_photo1'):
            survey_result.field_photo1 = request.POST.get('field_photo1')
        elif request.FILES.get('field_photo1'):
            # Just in case they still send a file, but URLField won't like it.
            pass
            
        if request.POST.get('field_photo2'):
            survey_result.field_photo2 = request.POST.get('field_photo2')
            
        if request.POST.get('field_photo3'):
            survey_result.field_photo3 = request.POST.get('field_photo3')
        elif request.FILES.get('field_photo3'):
            survey_result.field_photo3 = request.FILES.get('field_photo3')
            
        survey_result.survey_status = 'Completed'
        survey_result.save()
        
        survey.refresh_from_db()
        
        survey_data = {
            'survey_id': survey.survey_id,
            'title': survey.title or '-',
            'plot_code': survey.plot.plot_code if survey.plot else '-',
            'farmer_name': survey.plot.farmer.name if survey.plot and survey.plot.farmer else '-',
            'survey_stage': survey.survey_stage or '-',
            'survey_month': survey.survey_month or '-',
            'number_of_days': survey.number_of_days,
            'result_id': survey_result.id,
            'survey_date': survey_result.survey_date.strftime('%Y-%m-%d') if survey_result.survey_date else None,
            'survey_status': survey_result.survey_status,
            'completion_percentage': survey_result.completion_percentage,
            'description': survey.description or '-',
            'weed_infestation': survey_result.weed_infestation or '-',
            'tillering_vigour': survey_result.tillering_vigour or '-',
            'pest_incidence': survey_result.pest_incidence or '-',
            'disease_incidence': survey_result.disease_incidence or '-',
            'irrigation_status': survey_result.irrigation_status or '-',
            'nutrition_status': survey_result.nutrition_status or '-',
            'remarks': survey_result.remarks or '-',
            'field_photo1': survey_result.field_photo1 if survey_result.field_photo1 else None,
            'field_photo2': survey_result.field_photo2 if survey_result.field_photo2 else None,
            'field_photo3': survey_result.field_photo3 if survey_result.field_photo3 else None,
        }
        
        return JsonResponse({
            "status": "success", 
            "message": "Survey updated successfully",
            "data": survey_data
        })
        
    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)