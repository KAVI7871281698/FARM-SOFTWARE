from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from .models import Role, Officer, Section, Village, Farmer, Variety, Crop, Group, Factory, Division, WorkAssign, Plot, SoilType, ScoutingLog

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

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def index(request):
    if request.method == 'POST':
        keys = request.POST.keys()
        
        # ==========================================
        # 1. MOBILE API: Add Plot Delegation
        # ==========================================
        if 'farmer_name' in keys and 'officer_id' in keys:
            return api_add_plot(request)
            
        # ==========================================
        # 3. MOBILE API & WEB: Login
        # ==========================================
        elif 'user_id' in keys and 'password' in keys:
            user_id = request.POST.get('user_id')
            password = request.POST.get('password')
            
            # Check if this is from Mobile App (e.g. they pass device_id, lt, or ln)
            is_mobile = 'device_id' in keys or 'lt' in keys or 'ln' in keys
            
            user = Officer.objects.filter(user_id=user_id, password=password).first()
            
            if is_mobile:
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
            else:
                # Web Login Logic
                if user:
                    request.session['user_id'] = user.user_id
                    request.session['officer_name'] = user.name
                    request.session['permissions'] = user.permissions or []
                    request.session['role_id'] = user.role_id
                    request.session['group_id'] = user.group_id if user.group else None
                    request.session['role_name'] = user.role.name if user.role else ''
                    request.session['factory_ids'] = user.factory_ids
                    return redirect('dashboard')
                else:
                    messages.error(request, 'Invalid User ID or password.')
                    return redirect('index')

        # ==========================================
        # 4. MOBILE API: Get Work Assigns
        # ==========================================
        elif 'officer_id' in keys and 'device_id' in keys and 'plot_action' not in keys and 'get_farmers' not in keys and 'crop_id' not in keys:
            officer_id = request.POST.get('officer_id')
            device_id = request.POST.get('device_id')
            lt = request.POST.get('lt')
            ln = request.POST.get('ln')
            
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
                            'id': p.id,
                            'plot_code': p.plot_code,
                            'farmer_name': p.farmer.name if p.farmer else None,
                            'farmer_phone': p.farmer.phone if p.farmer else None,
                            'crop_name': p.crop_type.crop_name if p.crop_type else None,
                            'variety_name': p.variety.variety_name if p.variety else None,
                            'area_acre': str(p.area_acre) if p.area_acre is not None else None,
                            'status': p.status,
                            'soil_name': p.soil_type.soil_name if p.soil_type else None,
                            'latitude': p.latitude,
                            'longitude': p.longitude,
                            'date_planted': str(p.planting_date) if p.planting_date else None,
                        })

                data.append({
                    'id': wa.id,
                    'work_assign_code': wa.work_assign_code,
                    'division': wa.division,
                    'section_id': wa.section.id if wa.section else None,
                    'section_name': wa.section.section_name if wa.section else None,
                    'village_id': wa.village.id if wa.village else None,
                    'village_name': wa.village.village_name if wa.village else None,
                    'status': wa.status,
                    'plots': village_plots
                })
            
            return JsonResponse({
                'status': 'success',
                'message': 'Work assigns fetched successfully',
                'data': data
            })
            
        # ==========================================
        # 5. MOBILE API: Get Farmers
        # ==========================================
        elif request.POST.get('get_farmers', '').lower() == 'true':
            group_id = request.POST.get('group_id')
            device_id = request.POST.get('device_id')
            lt = request.POST.get('lt')
            ln = request.POST.get('ln')
            
            farmers = Farmer.objects.filter(group_id=group_id) if group_id else Farmer.objects.all()
            data = []
            for f in farmers:
                village_name = f.village.village_name if f.village else "No Village"
                display_name = f"{f.name} - {village_name}"
                data.append({
                    'id': f.id,
                    'farmer_code': f.farmer_code,
                    'farmer_name': display_name
                })
                
            return JsonResponse({
                'status': 'success',
                'message': 'Farmers fetched successfully',
                'data': data
            })
            
        # ==========================================
        # 6. MOBILE API: Get Varieties
        # ==========================================
        elif 'crop_id' in keys and 'group_id' in keys and 'device_id' in keys:
            crop_id = request.POST.get('crop_id')
            group_id = request.POST.get('group_id')
            device_id = request.POST.get('device_id')
            lt = request.POST.get('lt')
            ln = request.POST.get('ln')
            
            varieties = Variety.objects.filter(crop_type_id=crop_id)
            data = [{'id': v.id, 'variety_code': v.variety_code, 'variety_name': v.variety_name} for v in varieties]
            return JsonResponse({
                'status': 'success',
                'message': 'Varieties fetched successfully',
                'data': data
            })
            
        # ==========================================
        # 6. MOBILE API: Get Crops
        # ==========================================
        elif 'group_id' in keys and 'device_id' in keys and 'officer_id' not in keys:
            group_id = request.POST.get('group_id')
            device_id = request.POST.get('device_id')
            lt = request.POST.get('lt')
            ln = request.POST.get('ln')
            
            # Retrieve all crops
            crops = Crop.objects.all()
            data = [{'id': c.id, 'crop_code': c.crop_code, 'crop_name': c.crop_name} for c in crops]
            return JsonResponse({
                'status': 'success',
                'message': 'Crops fetched successfully',
                'data': data
            })

        # ==========================================
        # 7. MOBILE API: Get Plots
        # ==========================================
        elif request.POST.get('plot_action', '').lower() == 'true':
            return api_get_plots(request)

        # ==========================================
        # 8. MOBILE API: Get Soil Types
        # ==========================================
        elif request.POST.get('get_soil_types', '').lower() == 'true' and 'device_id' in keys:
            device_id = request.POST.get('device_id')
            lt = request.POST.get('lt')
            ln = request.POST.get('ln')
            
            soil_types = SoilType.objects.all()
            data = [{'id': s.id, 'soil_code': s.soil_code, 'soil_name': s.soil_name} for s in soil_types]
            return JsonResponse({
                'status': 'success',
                'message': 'Soil types fetched successfully',
                'data': data
            })

        # ==========================================
        # 9. MOBILE API: Add Scouting Log
        # ==========================================
        elif request.POST.get('add_scouting_log', '').lower() == 'true':
            plot_id = request.POST.get('plot_id')
            officer_id = request.POST.get('officer_id')
            
            plant_height = request.POST.get('plant_height')
            growth_stage = request.POST.get('growth_stage')
            
            pest_presence = request.POST.get('pest_presence', '').lower() in ['true', '1', 'yes']
            pest_type = request.POST.get('pest_type')
            pest_severity = request.POST.get('pest_severity')
            
            disease_presence = request.POST.get('disease_presence', '').lower() in ['true', '1', 'yes']
            disease_type = request.POST.get('disease_type')
            disease_photo = request.FILES.get('disease_photo')
            
            water_sufficiency = request.POST.get('water_sufficiency')
            water_stress_symptoms = request.POST.get('water_stress_symptoms', '').lower() in ['true', '1', 'yes']
            
            nutrient_deficiency = request.POST.get('nutrient_deficiency', '').lower() in ['true', '1', 'yes']
            deficiency_symptoms = request.POST.get('deficiency_symptoms')
            fertilizer_recommendation = request.POST.get('fertilizer_recommendation')

            try:
                plot = Plot.objects.get(id=plot_id)
                officer = Officer.objects.filter(id=officer_id).first() if officer_id else None
                
                scout_log = ScoutingLog.objects.create(
                    group=plot.group,
                    group_name=plot.group_name,
                    factory=plot.factory,
                    division=plot.division,
                    section=plot.section,
                    village=plot.village,
                    plot=plot,
                    officer=officer,
                    plant_height=plant_height,
                    growth_stage=growth_stage,
                    pest_presence=pest_presence,
                    pest_type=pest_type,
                    pest_severity=pest_severity,
                    disease_presence=disease_presence,
                    disease_type=disease_type,
                    disease_photo=disease_photo,
                    water_sufficiency=water_sufficiency,
                    water_stress_symptoms=water_stress_symptoms,
                    nutrient_deficiency=nutrient_deficiency,
                    deficiency_symptoms=deficiency_symptoms,
                    fertilizer_recommendation=fertilizer_recommendation
                )
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Scouting log added successfully',
                    'data': {
                        'log_id': scout_log.id,
                        'plot_id': scout_log.plot.id if scout_log.plot else None,
                        'plot_code': scout_log.plot.plot_code if scout_log.plot else None,
                        'officer_id': scout_log.officer.id if scout_log.officer else None,
                        'plant_height': scout_log.plant_height,
                        'growth_stage': scout_log.growth_stage,
                        'pest_presence': scout_log.pest_presence,
                        'pest_type': scout_log.pest_type,
                        'pest_severity': scout_log.pest_severity,
                        'disease_presence': scout_log.disease_presence,
                        'disease_type': scout_log.disease_type,
                        'disease_photo_url': scout_log.disease_photo.url if scout_log.disease_photo else None,
                        'water_sufficiency': scout_log.water_sufficiency,
                        'water_stress_symptoms': scout_log.water_stress_symptoms,
                        'nutrient_deficiency': scout_log.nutrient_deficiency,
                        'deficiency_symptoms': scout_log.deficiency_symptoms,
                        'fertilizer_recommendation': scout_log.fertilizer_recommendation,
                        'created_at': scout_log.created_at.isoformat() if scout_log.created_at else None
                    }
                })
            except Plot.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Plot not found'}, status=404)
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

        # Invalid API Request fallback
        elif request.headers.get('Accept') == 'application/json':
            return JsonResponse({'status': 'error', 'message': 'Unknown API request parameters'}, status=400)

    # GET request: Web Login Page
    return render(request, 'index.html')

def logout_view(request):
    request.session.flush()
    return redirect('index')

def get_allowed_factories(request):
    is_superadmin = (str(request.session.get('role_id')) == '1')
    if is_superadmin:
        return Factory.objects.all()
    
    factory_ids_str = request.session.get('factory_ids')
    if factory_ids_str:
        fids = [int(x.strip()) for x in factory_ids_str.split(',') if x.strip().isdigit()]
        return Factory.objects.filter(id__in=fids)
    return Factory.objects.none()

def get_active_factory_id(request):
    return request.session.get('active_factory_id', 'all')

def filter_by_factory(queryset, factory_path, request):
    active_id = get_active_factory_id(request)
    if active_id != 'all' and active_id:
        return queryset.filter(**{factory_path: active_id})
    else:
        is_superadmin = (str(request.session.get('role_id')) == '1')
        if not is_superadmin:
            allowed_factories = get_allowed_factories(request)
            return queryset.filter(**{f"{factory_path}__in": allowed_factories})
        return queryset

def dashboard(request):
    logged_group_id = request.session.get('group_id')
    role_name = request.session.get('role_name', '').lower()
    is_superadmin = (str(request.session.get('role_id')) == '1')
    
    try:
        if is_superadmin or not logged_group_id:
            groups = list(Group.objects.all())
        else:
            groups = list(Group.objects.filter(id=logged_group_id))
    except Exception as e:
        groups = []
        
    if not is_superadmin and logged_group_id:
        selected_group_id = str(logged_group_id)
        all_selected = False
    else:
        selected_group_id = request.GET.get('group', 'all')
        all_selected = (selected_group_id == 'all')
    for group in groups:
        group.is_selected = (str(group.id) == selected_group_id)
        
    factories = []
    divisions = []
    sections = []

    if 'factory' in request.GET:
        selected_factory_id = request.GET.get('factory', 'all')
        request.session['active_factory_id'] = selected_factory_id
    else:
        selected_factory_id = request.session.get('active_factory_id', 'all')

    selected_division_id = request.GET.get('division', 'all')
    selected_section_id = request.GET.get('section', 'all')

    if not all_selected:
        if not is_superadmin:
            allowed_factories_qs = get_allowed_factories(request)
            factories = list(allowed_factories_qs.filter(group_id=selected_group_id))
        else:
            factories = list(Factory.objects.filter(group_id=selected_group_id))
        
        if selected_factory_id != 'all' and not any(str(f.id) == selected_factory_id for f in factories):
            selected_factory_id = 'all'

        if selected_factory_id != 'all':
            divisions = list(Division.objects.filter(factory_name_id=selected_factory_id))
        else:
            divisions = list(Division.objects.filter(factory_name__group_id=selected_group_id))
            
        if selected_division_id != 'all' and not any(str(d.id) == selected_division_id for d in divisions):
            selected_division_id = 'all'
            
        if selected_division_id != 'all':
            sections = list(Section.objects.filter(division_id=selected_division_id))
        else:
            if selected_factory_id != 'all':
                sections = list(Section.objects.filter(division__factory_name_id=selected_factory_id))
            else:
                sections = list(Section.objects.filter(division__factory_name__group_id=selected_group_id))
                
        if selected_section_id != 'all' and not any(str(s.id) == selected_section_id for s in sections):
            selected_section_id = 'all'

    for f in factories:
        f.is_selected = (str(f.id) == selected_factory_id)
    for d in divisions:
        d.is_selected = (str(d.id) == selected_division_id)
    for s in sections:
        s.is_selected = (str(s.id) == selected_section_id)

    all_factories_selected = (selected_factory_id == 'all')
    all_divisions_selected = (selected_division_id == 'all')
    all_sections_selected = (selected_section_id == 'all')
    
    if not all_selected:
        # Dynamic counts for selected group
        factories_count = len(factories)
        divisions_count = len(divisions)
        sections_count = len(sections)
        
        if selected_section_id != 'all':
            farmers_count = Farmer.objects.filter(section_id=selected_section_id).count()
        else:
            farmers_count = Farmer.objects.filter(section__in=sections).count()
            
        if selected_division_id != 'all':
            officers_count = sum(1 for o in Officer.objects.all() if str(selected_division_id) in (o.division_ids or "").split(','))
        else:
            valid_div_ids = set(str(d.id) for d in divisions)
            officers_count = sum(1 for o in Officer.objects.all() if any(div_id in valid_div_ids for div_id in (o.division_ids or "").split(',')))
            
        groups_count = 1
        
        context = {
            'groups': groups,
            'all_selected': all_selected,
            'total_plots': 45,
            'mapped': 30,
            'unmapped': 15,
            'avg_ndvi': 0.65,
            'need_attention': 4,
            'damage_reports': 1,
            'overdue_scouts': 2,
            'groups_count': groups_count,
            'factories_count': factories_count,
            'divisions_count': divisions_count,
            'sections_count': sections_count,
            'farmers_count': farmers_count,
            'officers_count': officers_count,
            'factories': factories,
            'divisions': divisions,
            'sections': sections,
            'all_factories_selected': all_factories_selected,
            'all_divisions_selected': all_divisions_selected,
            'all_sections_selected': all_sections_selected,
        }
    else:
        # Dynamic counts for all groups
        if not is_superadmin:
            allowed_factories_qs = get_allowed_factories(request)
            factories = list(allowed_factories_qs)
        else:
            factories = list(Factory.objects.all())
        divisions = list(Division.objects.filter(factory_name__in=factories)) if not is_superadmin else list(Division.objects.all())
        sections = list(Section.objects.filter(division__in=divisions)) if not is_superadmin else list(Section.objects.all())
        
        
        groups_count = len(groups)
        factories_count = len(factories)
        divisions_count = len(divisions)
        sections_count = len(sections)
        farmers_count = Farmer.objects.count() if is_superadmin else Farmer.objects.filter(section__in=sections).count()
        if is_superadmin:
            officers_count = Officer.objects.count()
        else:
            valid_div_ids = set(str(d.id) for d in divisions)
            officers_count = sum(1 for o in Officer.objects.all() if any(div_id in valid_div_ids for div_id in (o.division_ids or "").split(',')))
        

        context = {
            'groups': groups,
            'all_selected': all_selected,
            'total_plots': 124,
            'mapped': 98,
            'unmapped': 18,
            'avg_ndvi': 0.72,
            'need_attention': 12,
            'damage_reports': 5,
            'overdue_scouts': 8,
            'groups_count': groups_count,
            'factories_count': factories_count,
            'divisions_count': divisions_count,
            'sections_count': sections_count,
            'farmers_count': farmers_count,
            'officers_count': officers_count,
            'factories': factories,
            'divisions': divisions,
            'sections': sections,
            'all_factories_selected': True,
            'all_divisions_selected': True,
            'all_sections_selected': True,
        }
    hierarchy_data = []
    active_groups = groups if all_selected else [g for g in groups if str(g.id) == selected_group_id]
    
    for g in active_groups:
        group_factories = [f for f in factories if f.group_id == g.id]
        group_data = {
            'name': g.name,
            'factories_count': len(group_factories),
            'factories': []
        }
        for f in group_factories:
            factory_divisions = [d for d in divisions if d.factory_name_id == f.id]
            factory_data = {
                'name': f.name,
                'divisions_count': len(factory_divisions),
                'divisions': []
            }
            for d in factory_divisions:
                division_sections = [s for s in sections if s.division_id == d.id]
                division_data = {
                    'name': d.name,
                    'sections_count': len(division_sections),
                    'sections': [{'name': s.section_name} for s in division_sections]
                }
                factory_data['divisions'].append(division_data)
            group_data['factories'].append(factory_data)
        hierarchy_data.append(group_data)
        
    context['hierarchy_data'] = hierarchy_data
    context['user_factories'] = get_allowed_factories(request) if not is_superadmin else Factory.objects.all()
    context['is_superadmin'] = is_superadmin
    context['active_factory_id'] = selected_factory_id

    user_id = request.session.get('user_id')
    if is_superadmin:
        work_assigns_count = WorkAssign.objects.count()
    else:
        work_assigns_count = WorkAssign.objects.filter(officer__user_id=user_id).count()
    context['work_assigns_count'] = work_assigns_count

    return render(request, 'dashboard.html', context)


def officers(request):
    logged_group_id = request.session.get('group_id')
    role_name = request.session.get('role_name', '').lower()
    is_superadmin = (str(request.session.get('role_id')) == '1')

    if is_superadmin or not logged_group_id:
        officers_list = Officer.objects.all()
    else:
        officers_list = Officer.objects.filter(group_id=logged_group_id)

    for officer in officers_list:
        display_divs = parse_legacy_field(officer.division_names)
        officer.display_divisions = ", ".join(display_divs) if display_divs else "-"
    return render(request, 'officers.html', {'officers': officers_list})

def field_intelligence(request):
    base_plots = Plot.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
    plots = filter_by_factory(base_plots, 'farmer__section__division__factory_name_id', request)
    
    plots_data = []
    for p in plots:
        try:
            # Handle potential JSON parsing issues if stored weirdly
            lat_str = str(p.latitude).strip("[]'\"")
            lon_str = str(p.longitude).strip("[]'\"")
            if not lat_str or not lon_str:
                continue
            
            lat = float(lat_str)
            lon = float(lon_str)
            
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
        except (ValueError, TypeError):
            continue

    context = {
        'plots_json': json.dumps(plots_data)
    }
    return render(request, 'field_intelligence.html', context)

def analytics(request):
    return render(request, 'analytics.html')

def ndvi_monitoring(request):
    return render(request, 'ndvi_monitoring.html')

def scouting(request):
    # Fetch allowed plots for dropdown
    plots = filter_by_factory(Plot.objects.all(), 'farmer__section__division__factory_name_id', request)

    if request.method == 'POST':
        plot_id = request.POST.get('plot_id')
        plant_height = request.POST.get('plant_height')
        growth_stage = request.POST.get('growth_stage')
        pest_presence = request.POST.get('pest_presence') == 'on'
        pest_type = request.POST.get('pest_type')
        pest_severity = request.POST.get('pest_severity')
        disease_presence = request.POST.get('disease_presence') == 'on'
        disease_type = request.POST.get('disease_type')
        disease_photo = request.FILES.get('disease_photo')
        water_sufficiency = request.POST.get('water_sufficiency')
        water_stress_symptoms = request.POST.get('water_stress_symptoms') == 'on'
        nutrient_deficiency = request.POST.get('nutrient_deficiency') == 'on'
        deficiency_symptoms = request.POST.get('deficiency_symptoms')
        fertilizer_recommendation = request.POST.get('fertilizer_recommendation')

        user_id = request.session.get('user_id')
        officer = Officer.objects.filter(user_id=user_id).first() if user_id else None

        if plot_id:
            plot = Plot.objects.get(id=plot_id)
            ScoutingLog.objects.create(
                group=plot.group,
                group_name=plot.group_name,
                factory=plot.factory,
                division=plot.division,
                section=plot.section,
                village=plot.village,
                plot=plot,
                officer=officer,
                plant_height=plant_height,
                growth_stage=growth_stage,
                pest_presence=pest_presence,
                pest_type=pest_type,
                pest_severity=pest_severity,
                disease_presence=disease_presence,
                disease_type=disease_type,
                disease_photo=disease_photo,
                water_sufficiency=water_sufficiency,
                water_stress_symptoms=water_stress_symptoms,
                nutrient_deficiency=nutrient_deficiency,
                deficiency_symptoms=deficiency_symptoms,
                fertilizer_recommendation=fertilizer_recommendation
            )
            messages.success(request, 'Scouting log added successfully!')
            return redirect('scout_logs')

    # Fetch logs history
    logs = filter_by_factory(ScoutingLog.objects.all(), 'plot__farmer__section__division__factory_name_id', request).order_by('-created_at')
    
    return render(request, 'scouting.html', {'plots': plots, 'logs': logs})

def scout_logs(request):
    logs = filter_by_factory(ScoutingLog.objects.all(), 'plot__farmer__section__division__factory_name_id', request).order_by('-created_at')
    return render(request, 'scout_logs.html', {'logs': logs})

def edit_scout_log(request, id):
    log = ScoutingLog.objects.get(id=id)
    plots = filter_by_factory(Plot.objects.all(), 'farmer__section__division__factory_name_id', request)
    
    if request.method == 'POST':
        plot_id = request.POST.get('plot_id')
        if plot_id:
            plot = Plot.objects.get(id=plot_id)
            log.plot = plot
            log.group = plot.group
            log.group_name = plot.group_name
            log.factory = plot.factory
            log.division = plot.division
            log.section = plot.section
            log.village = plot.village

        log.plant_height = request.POST.get('plant_height')
        log.growth_stage = request.POST.get('growth_stage')
        
        log.pest_presence = request.POST.get('pest_presence') == 'on'
        log.pest_type = request.POST.get('pest_type')
        log.pest_severity = request.POST.get('pest_severity')
        
        log.disease_presence = request.POST.get('disease_presence') == 'on'
        log.disease_type = request.POST.get('disease_type')
        if request.FILES.get('disease_photo'):
            log.disease_photo = request.FILES.get('disease_photo')
            
        log.water_sufficiency = request.POST.get('water_sufficiency')
        log.water_stress_symptoms = request.POST.get('water_stress_symptoms') == 'on'
        
        log.nutrient_deficiency = request.POST.get('nutrient_deficiency') == 'on'
        log.deficiency_symptoms = request.POST.get('deficiency_symptoms')
        log.fertilizer_recommendation = request.POST.get('fertilizer_recommendation')

        log.save()
        messages.success(request, 'Scouting log updated successfully!')
        return redirect('scout_logs')

    return render(request, 'edit_scout_log.html', {'log': log, 'plots': plots})

def delete_scout_log(request, id):
    log = ScoutingLog.objects.get(id=id)
    log.delete()
    messages.success(request, 'Scouting log deleted successfully!')
    return redirect('scout_logs')

def reports(request):
    return render(request, 'reports.html')

def settings(request):
    return render(request, 'settings.html')

def users(request):
    farmers_list = filter_by_factory(Farmer.objects.all(), 'section__division__factory_name_id', request)
    return render(request, 'users.html', {'farmers': farmers_list})

def villages(request):
    villages_list = filter_by_factory(Village.objects.all(), 'section__division__factory_name_id', request)
    return render(request, 'villages.html', {'villages': villages_list})

def sections(request):
    sections_list = filter_by_factory(Section.objects.all(), 'division__factory_name_id', request)
    return render(request, 'sections.html', {'sections': sections_list})

def varieties(request):
    varieties_list = Variety.objects.all()
    return render(request, 'varieties.html', {'varieties': varieties_list})

def plots(request):
    plots_list = filter_by_factory(Plot.objects.all(), 'farmer__section__division__factory_name_id', request)
    return render(request, 'plots.html', {'plots': plots_list})

def surveys(request):
    return render(request, 'surveys.html')

def add_farmer(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        father_name = request.POST.get('father_name')
        phone = request.POST.get('phone')
        division = request.POST.get('division')
        section_id = request.POST.get('section_id')
        village_id = request.POST.get('village_id')
        group_id = request.POST.get('group_id') or request.session.get('group_id')
        factory_id = request.session.get('active_factory_id')
        if factory_id == 'all':
            factory_id = None
            
        section = Section.objects.get(id=section_id) if section_id else None
        village = Village.objects.get(id=village_id) if village_id else None
        group_obj = Group.objects.filter(id=group_id).first() if group_id else None
        group_name = group_obj.name if group_obj else None
        factory_obj = Factory.objects.filter(id=factory_id).first() if factory_id else None
        factory_name = factory_obj.name if factory_obj else None
        
        Farmer.objects.create(
            name=name,
            father_name=father_name,
            phone=phone,
            division=division,
            section=section,
            village=village,
            group=group_obj,
            group_name=group_name,
            factory=factory_obj,
            factory_name=factory_name
        )
        return redirect('users')

    divisions_list = filter_by_factory(Division.objects.all(), 'factory_name_id', request)
    sections_list = filter_by_factory(Section.objects.all(), 'division__factory_name_id', request)
    villages_list = filter_by_factory(Village.objects.all(), 'section__division__factory_name_id', request)
    groups = Group.objects.all()
    
    return render(request, 'add_farmer.html', {
        'divisions': divisions_list,
        'sections': sections_list,
        'villages': villages_list,
        'groups': groups
    })

def add_officer(request):
    logged_group_id = request.session.get('group_id')
    role_name = request.session.get('role_name', '').lower()
    is_superadmin = (str(request.session.get('role_id')) == '1')

    if request.method == 'POST':
        name = request.POST.get('name')
        mobile = request.POST.get('mobile')
        email = request.POST.get('email')
        password = request.POST.get('password', 'default123')
        role_id = request.POST.get('role')
        if not is_superadmin and logged_group_id:
            group_id = logged_group_id
        else:
            group_id = request.POST.get('group_id')
        factory_ids = request.POST.getlist('factories') or request.POST.getlist('factories[]')
        division_ids = request.POST.getlist('divisions') or request.POST.getlist('divisions[]')
        section_ids = request.POST.getlist('sections') or request.POST.getlist('sections[]')
        permissions = request.POST.getlist('permissions[]')
        
        role = Role.objects.filter(id=role_id).first() if role_id else None
        group = Group.objects.filter(id=group_id).first() if group_id else None
        
        factory_names = list(Factory.objects.filter(id__in=factory_ids).values_list('name', flat=True)) if factory_ids else []
        division_names = list(Division.objects.filter(id__in=division_ids).values_list('name', flat=True)) if division_ids else []
        section_names = list(Section.objects.filter(id__in=section_ids).values_list('section_name', flat=True)) if section_ids else []
        
        officer = Officer.objects.create(
            name=name,
            mobile=mobile,
            email=email,
            password=password,
            role=role,
            group=group,
            group_name=group.name if group else "",
            permissions=permissions,
            factory_ids=",".join(factory_ids) if factory_ids else "",
            factory_names=",".join(factory_names) if factory_names else "",
            division_ids=",".join(division_ids) if division_ids else "",
            division_names=",".join(division_names) if division_names else "",
            section_ids=",".join(section_ids) if section_ids else "",
            section_names=",".join(section_names) if section_names else ""
        )
            
        return redirect('officers')

    roles = Role.objects.all()
    divisions = Division.objects.all()
    if is_superadmin or not logged_group_id:
        groups = Group.objects.all()
    else:
        groups = Group.objects.filter(id=logged_group_id)
    superadmin_role = Role.objects.filter(name__iexact='superadmin').first()
    superadmin_role_id = str(superadmin_role.id) if superadmin_role else "1"
    return render(request, 'add_officer.html', {'roles': roles, 'divisions': divisions, 'groups': groups, 'superadmin_role_id': superadmin_role_id, 'is_superadmin': is_superadmin})

def add_plots(request):
    if request.method == 'POST':
        farmer_id = request.POST.get('farmer_id')
        division_id = request.POST.get('division_id')
        division_name = request.POST.get('division_name')
        section_id = request.POST.get('section_id')
        section_name = request.POST.get('section_name')
        village_id = request.POST.get('village_id')
        village_name = request.POST.get('village_name')
        crop_id = request.POST.get('crop_id')
        variety_id = request.POST.get('variety_id')
        area_acre = request.POST.get('area_acre')
        planting_date = request.POST.get('planting_date')
        status = request.POST.get('status', 'Not Mapped')
        soil_type_id = request.POST.get('soil_type_id')
        lt = request.POST.get('lt')
        ln = request.POST.get('ln')
        device_id = request.POST.get('device_id')
        gps_area = request.POST.get('gps_area')
        planting_season = request.POST.get('planting_season')
        crushing_season = request.POST.get('crushing_season')
        plot_type = request.POST.get('plot_type')
        irrigation_type = request.POST.get('irrigation_type')
        water_source = request.POST.get('water_source')
        seed_type = request.POST.get('seed_type')
        spacing_ft = request.POST.get('spacing_ft')
        harvest_date = request.POST.get('harvest_date')
        production_t = request.POST.get('production_t')
        yield_ton_acre = request.POST.get('yield_ton_acre')

        farmer = Farmer.objects.filter(id=farmer_id).first() if farmer_id else None
        division = Division.objects.filter(id=division_id).first() if division_id else None
        section = Section.objects.filter(id=section_id).first() if section_id else None
        village = Village.objects.filter(id=village_id).first() if village_id else None
        crop = Crop.objects.filter(id=crop_id).first() if crop_id else None
        variety = Variety.objects.filter(id=variety_id).first() if variety_id else None
        soil_type = SoilType.objects.filter(id=soil_type_id).first() if soil_type_id else None
        
        group_obj = farmer.group if farmer else None
        group_name = farmer.group_name if farmer else None
        factory_obj = farmer.factory if farmer else None
        factory_name = farmer.factory_name if farmer else None

        Plot.objects.create(
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
            device_id=device_id,
            gps_area=gps_area if gps_area else None,
            planting_season=planting_season,
            crushing_season=crushing_season,
            plot_type=plot_type,
            irrigation_type=irrigation_type,
            water_source=water_source,
            seed_type=seed_type,
            spacing_ft=spacing_ft if spacing_ft else None,
            harvest_date=harvest_date if harvest_date else None,
            production_t=production_t if production_t else None,
            yield_ton_acre=yield_ton_acre if yield_ton_acre else None,
            group=group_obj,
            group_name=group_name,
            factory=factory_obj,
            factory_name=factory_name
        )
        return redirect('plots')

    active_factory_id = request.session.get('active_factory_id', 'all')
    if active_factory_id != 'all':
        farmers_list = Farmer.objects.filter(section__division__factory_name_id=active_factory_id)
    else:
        logged_group_id = request.session.get('group_id')
        if logged_group_id:
            farmers_list = Farmer.objects.filter(section__division__factory_name__group_id=logged_group_id)
        else:
            farmers_list = Farmer.objects.all()
            
    crops_list = Crop.objects.all()
    varieties_list = Variety.objects.all()
    soil_types_list = SoilType.objects.all()
    return render(request, 'add_plots.html', {
        'farmers': farmers_list,
        'crops': crops_list,
        'varieties': varieties_list,
        'soil_types': soil_types_list
    })

def edit_plot(request, id):
    from django.shortcuts import get_object_or_404
    plot = get_object_or_404(Plot, id=id)
    if request.method == 'POST':
        farmer_id = request.POST.get('farmer_id')
        division_id = request.POST.get('division_id')
        division_name = request.POST.get('division_name')
        section_id = request.POST.get('section_id')
        section_name = request.POST.get('section_name')
        village_id = request.POST.get('village_id')
        village_name = request.POST.get('village_name')
        crop_id = request.POST.get('crop_id')
        variety_id = request.POST.get('variety_id')
        area_acre = request.POST.get('area_acre')
        planting_date = request.POST.get('planting_date')
        status = request.POST.get('status', 'Not Mapped')
        soil_type_id = request.POST.get('soil_type_id')
        lt = request.POST.get('lt')
        ln = request.POST.get('ln')
        gps_area = request.POST.get('gps_area')
        planting_season = request.POST.get('planting_season')
        crushing_season = request.POST.get('crushing_season')
        plot_type = request.POST.get('plot_type')
        irrigation_type = request.POST.get('irrigation_type')
        water_source = request.POST.get('water_source')
        seed_type = request.POST.get('seed_type')
        spacing_ft = request.POST.get('spacing_ft')
        harvest_date = request.POST.get('harvest_date')
        production_t = request.POST.get('production_t')
        yield_ton_acre = request.POST.get('yield_ton_acre')

        farmer = Farmer.objects.filter(id=farmer_id).first() if farmer_id else None
        division = Division.objects.filter(id=division_id).first() if division_id else None
        section = Section.objects.filter(id=section_id).first() if section_id else None
        village = Village.objects.filter(id=village_id).first() if village_id else None
        crop = Crop.objects.filter(id=crop_id).first() if crop_id else None
        variety = Variety.objects.filter(id=variety_id).first() if variety_id else None
        soil_type = SoilType.objects.filter(id=soil_type_id).first() if soil_type_id else None

        plot.farmer = farmer
        plot.division = division
        plot.division_name = division_name
        plot.section = section
        plot.section_name = section_name
        plot.village = village
        plot.village_name = village_name
        plot.crop_type = crop
        plot.variety = variety
        if planting_date:
            plot.planting_date = planting_date
        if area_acre:
            plot.area_acre = area_acre
        plot.status = status
        plot.soil_type = soil_type
        if lt:
            plot.latitude = lt
        if ln:
            plot.longitude = ln
            
        plot.gps_area = gps_area if gps_area else None
        plot.planting_season = planting_season
        plot.crushing_season = crushing_season
        plot.plot_type = plot_type
        plot.irrigation_type = irrigation_type
        plot.water_source = water_source
        plot.seed_type = seed_type
        plot.spacing_ft = spacing_ft if spacing_ft else None
        if harvest_date:
            plot.harvest_date = harvest_date
        else:
            plot.harvest_date = None
        plot.production_t = production_t if production_t else None
        plot.yield_ton_acre = yield_ton_acre if yield_ton_acre else None
        if farmer:
            plot.group = farmer.group
            plot.group_name = farmer.group_name
            plot.factory = farmer.factory
            plot.factory_name = farmer.factory_name
            
        plot.save()
        return redirect('plots')

    active_factory_id = request.session.get('active_factory_id', 'all')
    if active_factory_id != 'all':
        farmers_list = Farmer.objects.filter(section__division__factory_name_id=active_factory_id)
    else:
        logged_group_id = request.session.get('group_id')
        if logged_group_id:
            farmers_list = Farmer.objects.filter(section__division__factory_name__group_id=logged_group_id)
        else:
            farmers_list = Farmer.objects.all()

    crops_list = Crop.objects.all()
    varieties_list = Variety.objects.all()
    soil_types_list = SoilType.objects.all()
    return render(request, 'edit_plot.html', {
        'plot': plot,
        'farmers': farmers_list,
        'crops': crops_list,
        'varieties': varieties_list,
        'soil_types': soil_types_list
    })

def delete_plot(request, id):
    from django.shortcuts import get_object_or_404
    plot = get_object_or_404(Plot, id=id)
    plot.delete()
    return redirect('plots')

def add_section(request):
    if request.method == 'POST':
        section_name = request.POST.get('section_name')
        description = request.POST.get('description')
        division_id = request.POST.get('division_id')
        division = Division.objects.filter(id=division_id).first() if division_id else None
        
        Section.objects.create(
            section_name=section_name,
            description=description,
            division=division
        )
        return redirect('sections')

    active_factory_id = request.session.get('active_factory_id', 'all')
    if active_factory_id != 'all':
        divisions = Division.objects.filter(factory_name_id=active_factory_id)
    else:
        logged_group_id = request.session.get('group_id')
        if logged_group_id:
            divisions = Division.objects.filter(factory_name__group_id=logged_group_id)
        else:
            divisions = Division.objects.all()
    return render(request, 'add_section.html', {'divisions': divisions})

def add_survey(request):
    return render(request, 'add_survey.html')

def add_user(request):
    return render(request, 'add_user.html')

def add_variety(request):
    if request.method == 'POST':
        variety_name = request.POST.get('variety_name')
        crop_id = request.POST.get('crop_id')
        crop = Crop.objects.get(id=crop_id) if crop_id else None
        
        Variety.objects.create(
            variety_name=variety_name,
            crop_type=crop
        )
        return redirect('varieties')
    
    active_factory_id = request.session.get('active_factory_id', 'all')
    if active_factory_id != 'all':
        sections_list = Section.objects.filter(division__factory_name_id=active_factory_id)
    else:
        logged_group_id = request.session.get('group_id')
        if logged_group_id:
            sections_list = Section.objects.filter(division__factory_name__group_id=logged_group_id)
        else:
            sections_list = Section.objects.all()
    crops_list = Crop.objects.all()
    return render(request, 'add_variety.html', {'sections': sections_list, 'crops': crops_list})

def add_village(request):
    if request.method == 'POST':
        village_name = request.POST.get('village_name')
        division = request.POST.get('division')
        section_id = request.POST.get('section_id')
        taluk = request.POST.get('taluk')
        district = request.POST.get('district')
        state = request.POST.get('state')
        status = request.POST.get('status')
        description = request.POST.get('description')
        
        section = Section.objects.get(id=section_id) if section_id else None
        
        if section:
            Village.objects.create(
                village_name=village_name,
                division=division,
                section=section,
                taluk=taluk,
                district=district,
                state=state,
                status=status,
                description=description
            )
            return redirect('villages')

    divisions_list = filter_by_factory(Division.objects.all(), 'factory_name_id', request)
    sections_list = filter_by_factory(Section.objects.all(), 'division__factory_name_id', request)
    return render(request, 'add_village.html', {'sections': sections_list, 'divisions': divisions_list})

def edit_officer(request, id):
    from django.shortcuts import get_object_or_404
    officer = get_object_or_404(Officer, id=id)
    if request.method == 'POST':
        officer.name = request.POST.get('name')
        officer.mobile = request.POST.get('mobile')
        officer.email = request.POST.get('email')
        role_id = request.POST.get('role')
        officer.role = Role.objects.filter(id=role_id).first() if role_id else None
        group_id = request.POST.get('group_id')
        officer.group = Group.objects.filter(id=group_id).first() if group_id else None
        officer.group_name = officer.group.name if officer.group else ""
        
        factory_ids = request.POST.getlist('factories') or request.POST.getlist('factories[]')
        division_ids = request.POST.getlist('divisions') or request.POST.getlist('divisions[]')
        section_ids = request.POST.getlist('sections') or request.POST.getlist('sections[]')
        
        factory_names = list(Factory.objects.filter(id__in=factory_ids).values_list('name', flat=True)) if factory_ids else []
        division_names = list(Division.objects.filter(id__in=division_ids).values_list('name', flat=True)) if division_ids else []
        section_names = list(Section.objects.filter(id__in=section_ids).values_list('section_name', flat=True)) if section_ids else []
        
        officer.factory_ids = ",".join(factory_ids) if factory_ids else ""
        officer.factory_names = ",".join(factory_names) if factory_names else ""
        officer.division_ids = ",".join(division_ids) if division_ids else ""
        officer.division_names = ",".join(division_names) if division_names else ""
        officer.section_ids = ",".join(section_ids) if section_ids else ""
        officer.section_names = ",".join(section_names) if section_names else ""
        
        officer.permissions = request.POST.getlist('permissions[]')
        password = request.POST.get('password')
        if password:
            officer.password = password
        officer.save()
        
        return redirect('officers')
    
    roles = Role.objects.all()
    divisions = Division.objects.all()
    groups = Group.objects.all()
    superadmin_role = Role.objects.filter(name__iexact='superadmin').first()
    superadmin_role_id = str(superadmin_role.id) if superadmin_role else "1"
    
    officer_factory_ids = parse_legacy_field(officer.factory_ids)
    officer_factory_names = parse_legacy_field(officer.factory_names)
    officer_division_ids = parse_legacy_field(officer.division_ids)
    officer_division_names = parse_legacy_field(officer.division_names)
    officer_section_ids = parse_legacy_field(officer.section_ids)
    officer_section_names = parse_legacy_field(officer.section_names)

    officer_factories = zip(officer_factory_ids, officer_factory_names)
    officer_divisions = zip(officer_division_ids, officer_division_names)
    officer_sections = zip(officer_section_ids, officer_section_names)
    
    logged_group_id = request.session.get('group_id')
    is_superadmin = (str(request.session.get('role_id')) == '1')
    
    return render(request, 'edit_officer.html', {
        'officer': officer, 
        'roles': roles, 
        'divisions': divisions, 
        'groups': groups, 
        'superadmin_role_id': superadmin_role_id,
        'officer_factories': officer_factories,
        'officer_divisions': officer_divisions,
        'officer_sections': officer_sections,
        'is_superadmin': is_superadmin
    })

def edit_farmer(request, id):
    from django.shortcuts import get_object_or_404
    farmer = get_object_or_404(Farmer, id=id)
    if request.method == 'POST':
        farmer.name = request.POST.get('name')
        farmer.father_name = request.POST.get('father_name')
        farmer.phone = request.POST.get('phone')
        farmer.division = request.POST.get('division')
        section_id = request.POST.get('section_id')
        village_id = request.POST.get('village_id')
        group_id = request.POST.get('group_id') or request.session.get('group_id')
        factory_id = request.session.get('active_factory_id')
        if factory_id == 'all':
            factory_id = None
        
        farmer.section = Section.objects.get(id=section_id) if section_id else None
        farmer.village = Village.objects.get(id=village_id) if village_id else None
        group_obj = Group.objects.filter(id=group_id).first() if group_id else None
        farmer.group = group_obj
        farmer.group_name = group_obj.name if group_obj else None
        factory_obj = Factory.objects.filter(id=factory_id).first() if factory_id else None
        farmer.factory = factory_obj
        farmer.factory_name = factory_obj.name if factory_obj else None
        farmer.save()
        return redirect('users')

    sections_list = Section.objects.all()
    villages_list = Village.objects.all()
    groups = Group.objects.all()
    return render(request, 'edit_farmer.html', {
        'farmer': farmer,
        'sections': sections_list,
        'villages': villages_list,
        'groups': groups
    })

def edit_village(request, id):
    from django.shortcuts import get_object_or_404
    village = get_object_or_404(Village, id=id)
    if request.method == 'POST':
        village.village_name = request.POST.get('village_name')
        village.division = request.POST.get('division')
        section_id = request.POST.get('section_id')
        village.section = Section.objects.get(id=section_id) if section_id else None
        village.taluk = request.POST.get('taluk')
        village.district = request.POST.get('district')
        village.state = request.POST.get('state')
        village.status = request.POST.get('status')
        village.description = request.POST.get('description')
        village.save()
        return redirect('villages')

    divisions_list = filter_by_factory(Division.objects.all(), 'factory_name_id', request)
    sections_list = filter_by_factory(Section.objects.all(), 'division__factory_name_id', request)
    return render(request, 'edit_village.html', {'village': village, 'sections': sections_list, 'divisions': divisions_list})

def edit_section(request, id):
    from django.shortcuts import get_object_or_404
    section = get_object_or_404(Section, id=id)
    if request.method == 'POST':
        section.section_name = request.POST.get('section_name')
        section.description = request.POST.get('description')
        division_id = request.POST.get('division_id')
        section.division = Division.objects.filter(id=division_id).first() if division_id else None
        section.save()
        return redirect('sections')

    divisions = Division.objects.all()
    return render(request, 'edit_section.html', {'section': section, 'divisions': divisions})

def edit_variety(request, id):
    from django.shortcuts import get_object_or_404
    variety = get_object_or_404(Variety, id=id)
    if request.method == 'POST':
        variety.variety_name = request.POST.get('variety_name')
        crop_id = request.POST.get('crop_id')
        variety.crop_type = Crop.objects.get(id=crop_id) if crop_id else None
        variety.save()
        return redirect('varieties')
    
    sections_list = Section.objects.all()
    crops_list = Crop.objects.all()
    return render(request, 'edit_variety.html', {'variety': variety, 'sections': sections_list, 'crops': crops_list})

def roles(request):
    roles_list = Role.objects.all()
    return render(request, 'roles.html', {'roles': roles_list})

def add_role(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        Role.objects.create(name=name)
        return redirect('roles')
    return render(request, 'add_role.html')

def edit_role(request, id):
    from django.shortcuts import get_object_or_404
    role = get_object_or_404(Role, id=id)
    if request.method == 'POST':
        role.name = request.POST.get('name')
        role.save()
        return redirect('roles')
    return render(request, 'edit_role.html', {'role': role})

def groups(request):
    groups_list = Group.objects.all()
    return render(request, 'groups.html', {'groups': groups_list})

def add_group(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        
        Group.objects.create(
            name=name
        )
        return redirect('groups')

    return render(request, 'add_group.html')

def edit_group(request, id):
    from django.shortcuts import get_object_or_404
    group = get_object_or_404(Group, id=id)
    if request.method == 'POST':
        group.name = request.POST.get('name')
        group.save()
        return redirect('groups')

    return render(request, 'edit_group.html', {'group': group})

def factories(request):
    factories_list = filter_by_factory(Factory.objects.all(), 'id', request)
    return render(request, 'factories.html', {'factories': factories_list})

def add_factory(request):
    if request.method == 'POST':
        group_id = request.POST.get('group_id')
        name = request.POST.get('name')
        location_LatLong = request.POST.get('location_LatLong')
        crushing_capacity = request.POST.get('crushing_capacity')
        
        group = Group.objects.get(id=group_id) if group_id else None
        
        Factory.objects.create(
            group=group,
            name=name,
            location_LatLong=location_LatLong,
            crushing_capacity=crushing_capacity
        )
        return redirect('factories')

    groups_list = Group.objects.all()
    return render(request, 'add_factory.html', {'groups': groups_list})

def edit_factory(request, id):
    from django.shortcuts import get_object_or_404
    factory = get_object_or_404(Factory, id=id)
    if request.method == 'POST':
        group_id = request.POST.get('group_id')
        factory.group = Group.objects.get(id=group_id) if group_id else None
        factory.name = request.POST.get('name')
        factory.location_LatLong = request.POST.get('location_LatLong')
        factory.crushing_capacity = request.POST.get('crushing_capacity')
        factory.save()
        return redirect('factories')

    groups_list = Group.objects.all()
    return render(request, 'edit_factory.html', {'factory': factory, 'groups': groups_list})

def divisions(request):
    divisions_list = filter_by_factory(Division.objects.all(), 'factory_name_id', request)
    return render(request, 'divisions.html', {'divisions': divisions_list})

def add_division(request):
    if request.method == 'POST':
        factory_id = request.POST.get('factory_id')
        name = request.POST.get('name')
        
        factory = Factory.objects.get(id=factory_id) if factory_id else None
        
        Division.objects.create(
            factory_name=factory,
            name=name
        )
        return redirect('divisions')

    active_factory_id = request.session.get('active_factory_id', 'all')
    if active_factory_id != 'all':
        factories_list = Factory.objects.filter(id=active_factory_id)
    else:
        logged_group_id = request.session.get('group_id')
        if logged_group_id:
            factories_list = Factory.objects.filter(group_id=logged_group_id)
        else:
            factories_list = Factory.objects.all()
    return render(request, 'add_division.html', {'factories': factories_list})

def edit_division(request, id):
    from django.shortcuts import get_object_or_404
    division = get_object_or_404(Division, id=id)
    if request.method == 'POST':
        factory_id = request.POST.get('factory_id')
        division.factory_name = Factory.objects.get(id=factory_id) if factory_id else None
        division.name = request.POST.get('name')
        division.save()
        return redirect('divisions')

    factories_list = Factory.objects.all()
    return render(request, 'edit_division.html', {'division': division, 'factories': factories_list})

def get_factories_by_group(request):
    group_id = request.GET.get('group_id')
    if group_id:
        factories = list(Factory.objects.filter(group_id=group_id).values('id', 'name'))
        return JsonResponse({'factories': factories})
    return JsonResponse({'factories': []})

def get_divisions_by_factories(request):
    factory_ids = request.GET.getlist('factory_ids') or request.GET.getlist('factory_ids[]')
    if factory_ids:
        divisions = list(Division.objects.filter(factory_name_id__in=factory_ids).values('id', 'name'))
        return JsonResponse({'divisions': divisions})
    return JsonResponse({'divisions': []})

def get_sections_by_divisions(request):
    division_ids = request.GET.getlist('division_ids') or request.GET.getlist('division_ids[]')
    if division_ids:
        sections = list(Section.objects.filter(division_id__in=division_ids).values('id', 'section_name'))
        return JsonResponse({'sections': sections})
    return JsonResponse({'sections': []})

def delete_officer(request, id):
    from django.shortcuts import get_object_or_404
    officer = get_object_or_404(Officer, id=id)
    officer.delete()
    return redirect('officers')

def delete_farmer(request, id):
    from django.shortcuts import get_object_or_404
    farmer = get_object_or_404(Farmer, id=id)
    farmer.delete()
    return redirect('users')

def delete_village(request, id):
    from django.shortcuts import get_object_or_404
    village = get_object_or_404(Village, id=id)
    village.delete()
    return redirect('villages')

def delete_section(request, id):
    from django.shortcuts import get_object_or_404
    section = get_object_or_404(Section, id=id)
    section.delete()
    return redirect('sections')

def delete_variety(request, id):
    from django.shortcuts import get_object_or_404
    variety = get_object_or_404(Variety, id=id)
    variety.delete()
    return redirect('varieties')

def delete_role(request, id):
    from django.shortcuts import get_object_or_404
    role = get_object_or_404(Role, id=id)
    role.delete()
    return redirect('roles')

def delete_group(request, id):
    from django.shortcuts import get_object_or_404
    group = get_object_or_404(Group, id=id)
    group.delete()
    return redirect('groups')

def delete_factory(request, id):
    from django.shortcuts import get_object_or_404
    factory = get_object_or_404(Factory, id=id)
    factory.delete()
    return redirect('factories')

def delete_division(request, id):
    from django.shortcuts import get_object_or_404
    division = get_object_or_404(Division, id=id)
    division.delete()
    return redirect('divisions')



from django.views.decorators.csrf import csrf_exempt

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
        
        if not officer_id:
            return JsonResponse({'status': 'error', 'message': 'officer_id is required'}, status=400)
            
        # Optional: You can log or use lt, ln, device_id here if needed
        
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
        
        return JsonResponse({
            'status': 'success',
            'message': 'Work assigns fetched successfully',
            'data': data
        })
        
    return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)

def work_assigns(request):
    if 'user_id' not in request.session:
        return redirect('index')

    work_list = WorkAssign.objects.all()
    # If we need factory/group filtering we can add it here. For now show all.

    return render(request, 'work_assigns.html', {'work_assigns': work_list})

def add_work_assign(request):
    if 'user_id' not in request.session:
        return redirect('index')

    if request.method == "POST":
        division_name = request.POST.get('division')
        section_id = request.POST.get('section_id')
        village_id = request.POST.get('village_id')
        officer_id = request.POST.get('officer_id')
        status = request.POST.get('status', 'active')

        section = Section.objects.get(id=section_id) if section_id else None
        village = Village.objects.get(id=village_id) if village_id else None
        officer = Officer.objects.get(id=officer_id) if officer_id else None

        WorkAssign.objects.create(
            division=division_name,
            section=section,
            village=village,
            officer=officer,
            status=status
        )
        return redirect('work_assigns')

    divisions = Division.objects.all()
    sections = Section.objects.all().select_related('division')
    villages = Village.objects.all().select_related('section')
    officers = Officer.objects.all()

    return render(request, 'add_work_assign.html', {
        'divisions': divisions,
        'sections': sections,
        'villages': villages,
        'officers': officers
    })

def edit_work_assign(request, id):
    if 'user_id' not in request.session:
        return redirect('index')

    work_assign = WorkAssign.objects.get(id=id)

    if request.method == "POST":
        work_assign.division = request.POST.get('division')
        section_id = request.POST.get('section_id')
        village_id = request.POST.get('village_id')
        officer_id = request.POST.get('officer_id')
        work_assign.status = request.POST.get('status', 'active')

        work_assign.section = Section.objects.get(id=section_id) if section_id else None
        work_assign.village = Village.objects.get(id=village_id) if village_id else None
        work_assign.officer = Officer.objects.get(id=officer_id) if officer_id else None
        
        work_assign.save()
        return redirect('work_assigns')

    divisions = Division.objects.all()
    sections = Section.objects.all().select_related('division')
    villages = Village.objects.all().select_related('section')
    officers = Officer.objects.all()

    return render(request, 'edit_work_assign.html', {
        'work_assign': work_assign,
        'divisions': divisions,
        'sections': sections,
        'villages': villages,
        'officers': officers
    })

def delete_work_assign(request, id):
    if 'user_id' not in request.session:
        return redirect('index')

    try:
        work_assign = WorkAssign.objects.get(id=id)
        work_assign.delete()
    except WorkAssign.DoesNotExist:
        pass
    
    return redirect('work_assigns')

def crops(request):
    if 'user_id' not in request.session:
        return redirect('index')
    crops_list = Crop.objects.all()
    return render(request, 'crops.html', {'crops': crops_list})

def add_crop(request):
    if 'user_id' not in request.session:
        return redirect('index')
    if request.method == 'POST':
        crop_name = request.POST.get('crop_name')
        Crop.objects.create(crop_name=crop_name)
        return redirect('crops')
    return render(request, 'add_crop.html')

def edit_crop(request, id):
    if 'user_id' not in request.session:
        return redirect('index')
    from django.shortcuts import get_object_or_404
    crop = get_object_or_404(Crop, id=id)
    if request.method == 'POST':
        crop.crop_name = request.POST.get('crop_name')
        crop.save()
        return redirect('crops')
    return render(request, 'edit_crop.html', {'crop': crop})

def delete_crop(request, id):
    if 'user_id' not in request.session:
        return redirect('index')
    try:
        crop = Crop.objects.get(id=id)
        crop.delete()
    except Crop.DoesNotExist:
        pass
    return redirect('crops')

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
                    boundary_img_val = request.POST.get('boundary_image')
                    try:
                        import json
                        plot.boundary_image = json.loads(boundary_img_val)
                    except:
                        plot.boundary_image = [boundary_img_val] if boundary_img_val else []
                
                if 'boundaries' in request.POST:
                    boundaries_val = request.POST.get('boundaries')
                    try:
                        import json
                        plot.boundaries = json.loads(boundaries_val)
                    except:
                        plot.boundaries = [boundaries_val] if boundaries_val else []
                
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

                boundary_img_val = request.POST.get('boundary_image')
                try:
                    import json
                    boundary_image_data = json.loads(boundary_img_val) if boundary_img_val else []
                except:
                    boundary_image_data = [boundary_img_val] if boundary_img_val else []

                boundaries_val = request.POST.get('boundaries')
                try:
                    import json
                    boundaries_data = json.loads(boundaries_val) if boundaries_val else []
                except:
                    boundaries_data = [boundaries_val] if boundaries_val else []

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
        except OSError as e:
            if e.errno == 30: # Read-only file system (Vercel)
                pass # Just ignore if we can't save on Vercel
            else:
                return JsonResponse({"status": "error", "message": f"File System Error: {str(e)}"}, status=400)
        except Exception as e:
            from django.core.exceptions import ValidationError
            error_msg = str(e)
            if isinstance(e, ValidationError):
                error_msg = "; ".join(e.messages)
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
                "boundaries": plot.boundaries if plot else None
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

def field_intelligence(request):
    if request.method == 'POST':
        farmer_id = request.POST.get('farmer_id')
        plot_id = request.POST.get('plot_id')
        boundary = request.POST.get('boundary') # JSON string
        img1 = request.FILES.get('img1')
        img2 = request.FILES.get('img2')
        img3 = request.FILES.get('img3')
        
        farmer = Farmer.objects.filter(id=farmer_id).first()
        plot = Plot.objects.filter(id=plot_id).first()
        
        if farmer and plot:
            mapping = FieldMapping(
                farmer=farmer,
                farmer_code=farmer.farmer_code,
                plot=plot,
                division=farmer.division,
                section=farmer.section.section_name if farmer.section else '',
                village=farmer.village.village_name if farmer.village else '',
                group=farmer.group,
                group_name=farmer.group_name,
                factory=farmer.factory,
                factory_name=farmer.factory_name,
                boundary=boundary,
                img1=img1,
                img2=img2,
                img3=img3,
                officer_name=request.session.get('officer_name')
            )
            mapping.save()
            
            plot.status = 'Mapped'
            plot.save()
            
            return redirect('field_intelligence')
            
    farmers = Farmer.objects.all()
    is_superadmin = request.session.get('role_id') == 1
    return render(request, 'field_intelligence.html', {
        'farmers': farmers,
        'is_superadmin': is_superadmin
    })

def soil_types(request):
    soil_types_list = SoilType.objects.all()
    return render(request, 'soil_types.html', {'soil_types': soil_types_list})

def add_soil_type(request):
    if request.method == 'POST':
        soil_name = request.POST.get('soil_name')
        SoilType.objects.create(soil_name=soil_name)
        return redirect('soil_types')
    return render(request, 'add_soil_type.html')

def edit_soil_type(request, id):
    from django.shortcuts import get_object_or_404
    soil_type = get_object_or_404(SoilType, id=id)
    if request.method == 'POST':
        soil_type.soil_name = request.POST.get('soil_name')
        soil_type.save()
        return redirect('soil_types')
    return render(request, 'edit_soil_type.html', {'soil_type': soil_type})

def delete_soil_type(request, id):
    from django.shortcuts import get_object_or_404
    soil_type = get_object_or_404(SoilType, id=id)
    soil_type.delete()
    return redirect('soil_types')