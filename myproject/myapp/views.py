from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
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
    # Check all keys that might contain boundary data
    for k in request.POST.keys():
        k_lower = k.lower()
        if 'boundar' in k_lower:
            if 'image' in k_lower:
                continue
            for val in request.POST.getlist(k):
                boundaries_list.append(val)
                
    if not boundaries_list:
        return None
        
    b_data = []
    for val in boundaries_list:
        try:
            import json
            parsed = json.loads(val)
            if isinstance(parsed, list):
                b_data.extend(parsed)
            else:
                b_data.append(parsed)
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
            import json
            parsed = json.loads(val)
            if isinstance(parsed, list):
                parsed_imgs.extend(parsed)
            else:
                if parsed:
                    parsed_imgs.append(parsed)
        except:
            if val:
                parsed_imgs.append(val)
    return parsed_imgs

def upload_file_to_supabase(file_obj, original_filename):
    import os
    import uuid
    from supabase import create_client, Client
    
    url = os.environ.get("SUPABASE_URL")
    if url and url.endswith('/rest/v1/'):
        url = url[:-9]
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        return None, "Supabase URL or Key missing in environment"
        
    try:
        supabase: Client = create_client(url, key)
        file_bytes = file_obj.read()
        file_obj.seek(0) # reset file pointer in case it's used again
        
        # Generate unique filename to avoid overwrites
        ext = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        
        res = supabase.storage.from_('plot_boundaries').upload(
            file=file_bytes,
            path=unique_filename,
            file_options={"content-type": getattr(file_obj, 'content_type', 'application/octet-stream')}
        )
        
        public_url = supabase.storage.from_('plot_boundaries').get_public_url(unique_filename)
        return public_url, None
    except Exception as e:
        print(f"Supabase upload error: {e}")
        return None, str(e)

from django.views.decorators.csrf import csrf_exempt
from .mobile_api_views import mobile_index_handler

@csrf_exempt
def index(request):
    if request.method == 'POST':
        response = mobile_index_handler(request)
        if response is not None:
            return response
            
        keys = request.POST.keys()
        if 'user_id' in keys and 'password' in keys:
            user_id = request.POST.get('user_id')
            password = request.POST.get('password')
            user = Officer.objects.filter(user_id=user_id, password=password).first()
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

    if 'factory' in request.GET:
        selected_factory_id = request.GET.get('factory', 'all')
        request.session['active_factory_id'] = selected_factory_id
    else:
        selected_factory_id = request.session.get('active_factory_id', 'all')

    if selected_factory_id != 'all':
        try:
            fac = Factory.objects.get(id=selected_factory_id)
            if fac.group_id:
                selected_group_id = str(fac.group_id)
                all_selected = False
        except:
            selected_factory_id = 'all'

    for group in groups:
        group.is_selected = (str(group.id) == selected_group_id)
        
    factories = []
    divisions = []
    sections = []



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

    # Calculate real data metrics for the dashboard
    from django.db.models import Avg, Q
    if selected_section_id != 'all':
        plots_qs = Plot.objects.filter(farmer__section_id=selected_section_id)
    elif selected_division_id != 'all':
        plots_qs = Plot.objects.filter(farmer__section__division_id=selected_division_id)
    elif selected_factory_id != 'all':
        plots_qs = Plot.objects.filter(farmer__section__division__factory_name_id=selected_factory_id)
    elif not all_selected:
        plots_qs = Plot.objects.filter(farmer__section__division__factory_name__group_id=selected_group_id)
    elif not is_superadmin:
        allowed_f_ids = [f.id for f in factories]
        plots_qs = Plot.objects.filter(farmer__section__division__factory_name_id__in=allowed_f_ids)
    else:
        plots_qs = Plot.objects.all()

    total_plots = plots_qs.count()
    mapped = plots_qs.filter(Q(boundaries__isnull=False) & ~Q(boundaries='')).count()
    unmapped = total_plots - mapped

    avg_ndvi_val = NDVIRecord.objects.filter(plot__in=plots_qs).aggregate(Avg('ndvi_value'))['ndvi_value__avg']
    avg_ndvi = round(avg_ndvi_val, 2) if avg_ndvi_val else 0.0

    need_attention = NDVIRecord.objects.filter(plot__in=plots_qs, health_status='Critical').values('plot').distinct().count()
    damage_reports = ScoutSurveyReport.objects.filter(scout__plot__in=plots_qs).exclude(pest_details='', disease_details='').count()
    overdue_scouts = Scout.objects.filter(plot__in=plots_qs, status='Pending Assignment').count()

    # Charts Data
    from datetime import date, timedelta
    import calendar
    today = date.today()
    six_months_ago = today.replace(day=1) - timedelta(days=5*30)
    six_months_ago = six_months_ago.replace(day=1)
    
    plot_ids = [p.id for p in plots_qs]
    
    ndvi_records = NDVIRecord.objects.filter(plot_id__in=plot_ids, date_recorded__gte=six_months_ago)
    monthly_ndvi = {}
    
    for i in range(5, -1, -1):
        d = today - timedelta(days=i*30)
        month_key = f"{d.year}-{d.month:02d}"
        month_label = calendar.month_abbr[d.month]
        monthly_ndvi[month_key] = {'label': month_label, 'total': 0, 'count': 0}
        
    for rec in ndvi_records:
        month_key = f"{rec.date_recorded.year}-{rec.date_recorded.month:02d}"
        if month_key in monthly_ndvi:
            monthly_ndvi[month_key]['total'] += float(rec.ndvi_value)
            monthly_ndvi[month_key]['count'] += 1
            
    ndvi_trend_labels = []
    ndvi_trend_data = []
    for key in sorted(monthly_ndvi.keys()):
        ndvi_trend_labels.append(monthly_ndvi[key]['label'])
        avg_val = monthly_ndvi[key]['total'] / monthly_ndvi[key]['count'] if monthly_ndvi[key]['count'] > 0 else 0
        ndvi_trend_data.append(round(avg_val, 2))

    # Fortnightly trend for Health and Stage
    unique_dates = list(ndvi_records.order_by('date_recorded').values_list('date_recorded', flat=True).distinct())
    unique_dates = unique_dates[-15:] if len(unique_dates) > 15 else unique_dates
    
    ht_labels = [d.strftime('%Y-%m-%d') for d in unique_dates]
    
    ht_health_data = { 'Good': [], 'Moderate': [], 'Need Attention': [] }
    ht_stage_data = { 'Germination': [], 'Early Tiller': [], 'Tillering': [], 'Grand growth': [], 'Maturity': [] }
    
    for d in unique_dates:
        records_for_date = ndvi_records.filter(date_recorded=d)
        ht_health_data['Good'].append(records_for_date.filter(health_status='Good').count())
        ht_health_data['Moderate'].append(records_for_date.filter(health_status='Moderate').count())
        ht_health_data['Need Attention'].append(records_for_date.filter(health_status='Need Attention').count())
        
        ht_stage_data['Germination'].append(records_for_date.filter(stage='Germination').count())
        ht_stage_data['Early Tiller'].append(records_for_date.filter(stage='Early Tiller').count())
        ht_stage_data['Tillering'].append(records_for_date.filter(stage='Tillering').count())
        ht_stage_data['Grand growth'].append(records_for_date.filter(stage='Grand growth').count())
        ht_stage_data['Maturity'].append(records_for_date.filter(stage='Maturity').count())

    health_counts = {'Healthy': 0, 'Moderate': 0, 'Critical': 0}
    for plot in plots_qs:
        latest_scout = plot.scouting_logs.order_by('-created_at').first()
        latest_ndvi = plot.ndvi_records.order_by('-date_recorded').first()
        
        health_status = 'Healthy'
        if latest_ndvi:
            health_status = latest_ndvi.health_status
        if latest_scout:
            if latest_scout.disease_presence:
                health_status = 'Critical'
            elif latest_scout.pest_presence or latest_scout.water_stress_symptoms or latest_scout.nutrient_deficiency:
                health_status = 'Moderate'
        if health_status in health_counts:
            health_counts[health_status] += 1
            
    scout_completed = Scout.objects.filter(plot_id__in=plot_ids, status='Completed').count()
    scout_pending = Scout.objects.filter(plot_id__in=plot_ids, status='Pending Assignment').count()
    scout_assigned = Scout.objects.filter(plot_id__in=plot_ids, status='Assigned').count()
    scout_status_data = [scout_completed, scout_pending, scout_assigned]

    surveys = Survey.objects.filter(plot_id__in=plot_ids)
    total_surveys = surveys.count()
    completed_surveys = sum(1 for s in surveys if s.status == 'Completed')
    if total_surveys > 0:
        survey_completed_perc = int((completed_surveys / total_surveys) * 100)
    else:
        survey_completed_perc = 100 if plot_ids else 0
    survey_completion_data = [survey_completed_perc, 100 - survey_completed_perc]

    import json
    context = {
        'groups': groups,
        'all_selected': all_selected,
        'total_plots': total_plots,
        'mapped': mapped,
        'unmapped': unmapped,
        'avg_ndvi': avg_ndvi,
        'need_attention': need_attention,
        'damage_reports': damage_reports,
        'overdue_scouts': overdue_scouts,
        'groups_count': groups_count,
        'factories_count': factories_count,
        'divisions_count': divisions_count,
        'sections_count': sections_count,
        'farmers_count': farmers_count,
        'officers_count': officers_count,
        'factories': factories,
        'divisions': divisions,
        'sections': sections,
        'all_factories_selected': selected_factory_id == 'all',
        'all_divisions_selected': selected_division_id == 'all',
        'all_sections_selected': selected_section_id == 'all',
        'ndvi_trend_labels_json': json.dumps(ndvi_trend_labels),
        'ndvi_trend_data_json': json.dumps(ndvi_trend_data),
        'health_counts_json': json.dumps([health_counts['Healthy'], health_counts['Moderate'], health_counts['Critical']]),
        'scout_status_data_json': json.dumps(scout_status_data),
        'survey_completion_data_json': json.dumps(survey_completion_data),
        'survey_perc': survey_completed_perc,
        'ht_labels_json': json.dumps(ht_labels),
        'ht_health_data_json': json.dumps(ht_health_data),
        'ht_stage_data_json': json.dumps(ht_stage_data)
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
    wa_qs = WorkAssign.objects.all()
    if selected_section_id != 'all':
        wa_qs = wa_qs.filter(section_id=selected_section_id)
    elif selected_division_id != 'all':
        wa_qs = wa_qs.filter(section__division_id=selected_division_id)
    elif selected_factory_id != 'all':
        wa_qs = wa_qs.filter(section__division__factory_name_id=selected_factory_id)
    elif not all_selected:
        wa_qs = wa_qs.filter(section__division__factory_name__group_id=selected_group_id)
    elif not is_superadmin:
        allowed_f_ids = [f.id for f in factories]
        wa_qs = wa_qs.filter(section__division__factory_name_id__in=allowed_f_ids)

    if not is_superadmin:
        wa_qs = wa_qs.filter(officer__user_id=user_id)
        
    work_assigns_count = wa_qs.count()
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

from django.db.models import Q

def field_intelligence(request):
    base_plots = Plot.objects.filter(
        Q(center_lt_ln__isnull=False) | 
        (Q(latitude__isnull=False) & Q(longitude__isnull=False))
    )
    plots = filter_by_factory(base_plots, 'farmer__section__division__factory_name_id', request)
    
    plots_data = []
    print("IN_VIEW_PLOTS_COUNT:", plots.count())
    for p in plots:
        try:
            lat, lon = None, None
            
            # First try center_lt_ln
            if p.center_lt_ln:
                if isinstance(p.center_lt_ln, list) and len(p.center_lt_ln) >= 2:
                    lat = float(p.center_lt_ln[0])
                    lon = float(p.center_lt_ln[1])
            
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

    context = {
        'plots_json': json.dumps(plots_data)
    }
    print("DEBUG PLOTS_JSON:", context['plots_json'])
    return render(request, 'field_intelligence.html', context)

def analytics(request):
    return render(request, 'analytics.html')


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
    surveys_list = list(Survey.objects.prefetch_related('results').all().order_by('-id'))
    
    active_count = 0
    pending_count = 0
    completed_surveys = 0
    
    for s in surveys_list:
        if s.status == 'Active':
            active_count += 1
        elif s.status == 'Pending':
            pending_count += 1
        elif s.status == 'Completed':
            completed_surveys += 1
            
    total = len(surveys_list)
    completion_rate = int((completed_surveys / total) * 100) if total > 0 else 0
    
    context = {
        'surveys': surveys_list,
        'active_count': active_count,
        'pending_count': pending_count,
        'completion_rate': completion_rate
    }
    return render(request, 'surveys.html', context)

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
    if request.method == 'POST':
        title = request.POST.get('title')
        plot_id = request.POST.get('plot_id')
        officer_id = request.POST.get('officer_id')
        survey_stage = request.POST.get('survey_stage')
        description = request.POST.get('description')
        survey_month = request.POST.get('survey_month')
        allocated_dates_raw = request.POST.get('allocated_dates')
        allocated_dates = [d.strip() for d in allocated_dates_raw.split(',')] if allocated_dates_raw else []
        days_count = len(allocated_dates)
        
        weed_infestation = request.POST.get('weed_infestation')
        tillering_vigour = request.POST.get('tillering_vigour')
        pest_incidence = request.POST.get('pest_incidence')
        disease_incidence = request.POST.get('disease_incidence')
        irrigation_status = request.POST.get('irrigation_status')
        nutrition_status = request.POST.get('nutrition_status')
        remarks = request.POST.get('remarks')
        
        field_photo1 = request.POST.get('field_photo1')
        field_photo2 = request.POST.get('field_photo2')
        field_photo3 = request.POST.get('field_photo3')
                
        plot = Plot.objects.filter(id=plot_id).first()
        officer = Officer.objects.filter(id=officer_id).first()
        
        if plot:
            survey = Survey(title=title, plot=plot, officer=officer, survey_stage=survey_stage, description=description, survey_month=survey_month, number_of_days=days_count, allocated_dates=allocated_dates)
            survey.save()
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

            result = SurveyResult(survey=survey, survey_date=survey_date, weed_infestation=weed_infestation, tillering_vigour=tillering_vigour, pest_incidence=pest_incidence, disease_incidence=disease_incidence, irrigation_status=irrigation_status, nutrition_status=nutrition_status, remarks=remarks)
            if field_photo1:
                result.field_photo1 = field_photo1
            if field_photo2:
                result.field_photo2 = field_photo2
            if field_photo3:
                result.field_photo3 = field_photo3
            result.survey_status = 'Completed'
            result.save()
            return redirect('surveys')
            
    plots = Plot.objects.all()
    officers = Officer.objects.all()
    return render(request, 'add_survey.html', {'plots': plots, 'officers': officers})

def edit_survey(request, id):
    survey = get_object_or_404(Survey, id=id)
    if request.method == 'POST':
        survey.title = request.POST.get('title')
        plot_id = request.POST.get('plot_id')
        if plot_id:
            survey.plot = Plot.objects.filter(id=plot_id).first()
        officer_id = request.POST.get('officer_id')
        if officer_id:
            survey.officer = Officer.objects.filter(id=officer_id).first()
            
        survey.survey_stage = request.POST.get('survey_stage')
        survey.description = request.POST.get('description')
        survey.survey_month = request.POST.get('survey_month')
        survey.status = request.POST.get('status', survey.status)
        
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

        result, _ = SurveyResult.objects.get_or_create(survey=survey, survey_date=survey_date)
        result.weed_infestation = request.POST.get('weed_infestation')
        result.tillering_vigour = request.POST.get('tillering_vigour')
        result.pest_incidence = request.POST.get('pest_incidence')
        result.disease_incidence = request.POST.get('disease_incidence')
        result.irrigation_status = request.POST.get('irrigation_status')
        result.nutrition_status = request.POST.get('nutrition_status')
        result.remarks = request.POST.get('remarks')
        if request.POST.get('field_photo1'):
            result.field_photo1 = request.POST.get('field_photo1')
        if request.POST.get('field_photo2'):
            result.field_photo2 = request.POST.get('field_photo2')
        if request.POST.get('field_photo3'):
            result.field_photo3 = request.POST.get('field_photo3')
        result.survey_status = 'Completed'
        result.save()
        
        allocated_dates_raw = request.POST.get('allocated_dates')
        if allocated_dates_raw:
            allocated_dates = [d.strip() for d in allocated_dates_raw.split(',')]
            survey.allocated_dates = allocated_dates
            survey.number_of_days = len(allocated_dates)
        else:
            survey.allocated_dates = []
            survey.number_of_days = 0
            
        survey.save()
        return redirect('surveys')
        
    plots = Plot.objects.all()
    officers = Officer.objects.all()
    return render(request, 'edit_survey.html', {'survey': survey, 'plots': plots, 'officers': officers})

def delete_survey(request, id):
    survey = get_object_or_404(Survey, id=id)
    survey.delete()
    return redirect('surveys')

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

def work_assigns(request):
    if 'user_id' not in request.session:
        return redirect('index')

    wa_qs = WorkAssign.objects.all()
    
    selected_group_id = request.GET.get('group', 'all')
    selected_factory_id = request.GET.get('factory', 'all')
    selected_division_id = request.GET.get('division', 'all')
    selected_section_id = request.GET.get('section', 'all')
    is_superadmin = (str(request.session.get('role_id')) == '1')
    logged_group_id = request.session.get('group_id')
    
    if not is_superadmin and logged_group_id:
        selected_group_id = str(logged_group_id)

    if selected_section_id != 'all':
        wa_qs = wa_qs.filter(section_id=selected_section_id)
    elif selected_division_id != 'all':
        wa_qs = wa_qs.filter(section__division_id=selected_division_id)
    elif selected_factory_id != 'all':
        wa_qs = wa_qs.filter(section__division__factory_name_id=selected_factory_id)
    elif selected_group_id != 'all':
        wa_qs = wa_qs.filter(section__division__factory_name__group_id=selected_group_id)
    elif not is_superadmin:
        allowed_f_ids = [int(x.strip()) for x in request.session.get('factory_ids', '').split(',') if x.strip().isdigit()]
        wa_qs = wa_qs.filter(section__division__factory_name_id__in=allowed_f_ids)

    if not is_superadmin:
        wa_qs = wa_qs.filter(officer__user_id=request.session.get('user_id'))

    return render(request, 'work_assigns.html', {'work_assigns': wa_qs})

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
            
    from django.db.models import Q
    base_plots = Plot.objects.filter(
        Q(center_lt_ln__isnull=False) | 
        (Q(latitude__isnull=False) & Q(longitude__isnull=False))
    )
    plots = filter_by_factory(base_plots, 'farmer__section__division__factory_name_id', request)
    
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
                        import json
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

    import json
    farmers = Farmer.objects.all()
    is_superadmin = request.session.get('role_id') == 1
    return render(request, 'field_intelligence.html', {
        'farmers': farmers,
        'is_superadmin': is_superadmin,
        'plots_json': json.dumps(plots_data)
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


# ==========================================
# NDVI Monitoring & Scout Management
# ==========================================

from .models import NDVIRecord, Scout, ScoutAssignment, ScoutSurveyReport

def ndvi_dashboard(request):
    from django.db.models import Q, Avg, Count
    from datetime import date, timedelta
    import calendar

    logged_group_id = request.session.get('group_id')
    role_name = request.session.get('role_name', '').lower()
    is_superadmin = (str(request.session.get('role_id')) == '1')
    
    # 1. Handle Filters (Group, Factory, Division, Section)
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

    if 'factory' in request.GET:
        selected_factory_id = request.GET.get('factory', 'all')
        request.session['active_factory_id'] = selected_factory_id
    else:
        selected_factory_id = request.session.get('active_factory_id', 'all')

    if selected_factory_id != 'all':
        try:
            fac = Factory.objects.get(id=selected_factory_id)
            if fac.group_id:
                selected_group_id = str(fac.group_id)
                all_selected = False
        except:
            selected_factory_id = 'all'
            
    for group in groups:
        group.is_selected = (str(group.id) == selected_group_id)

    factories = []
    divisions = []
    sections = []



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
    else:
        if not is_superadmin:
            allowed_factories_qs = get_allowed_factories(request)
            factories = list(allowed_factories_qs)
        else:
            factories = list(Factory.objects.all())
        divisions = list(Division.objects.filter(factory_name__in=factories)) if not is_superadmin else list(Division.objects.all())
        sections = list(Section.objects.filter(division__in=divisions)) if not is_superadmin else list(Section.objects.all())

    for f in factories:
        f.is_selected = (str(f.id) == selected_factory_id)
    for d in divisions:
        d.is_selected = (str(d.id) == selected_division_id)
    for s in sections:
        s.is_selected = (str(s.id) == selected_section_id)

    # Base Plot Query with Filters
    plots_query = Plot.objects.filter(Q(center_lt_ln__isnull=False) | Q(boundaries__isnull=False)).distinct()
    
    if selected_section_id != 'all':
        plots_query = plots_query.filter(farmer__section_id=selected_section_id)
    elif selected_division_id != 'all':
        plots_query = plots_query.filter(farmer__section__division_id=selected_division_id)
    elif selected_factory_id != 'all':
        plots_query = plots_query.filter(farmer__section__division__factory_name_id=selected_factory_id)
    elif not all_selected:
        plots_query = plots_query.filter(farmer__section__division__factory_name__group_id=selected_group_id)
    elif not is_superadmin:
        allowed_f_ids = get_allowed_factories(request).values_list('id', flat=True)
        plots_query = plots_query.filter(farmer__section__division__factory_name_id__in=allowed_f_ids)

    plots = list(plots_query)

    # Hierarchy Data
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

    # Real Data for Charts
    # 1. NDVI Trend (Last 6 Months)
    today = date.today()
    six_months_ago = today.replace(day=1) - timedelta(days=5*30) # Approx 6 months
    six_months_ago = six_months_ago.replace(day=1)
    
    plot_ids = [p.id for p in plots]
    
    ndvi_records = NDVIRecord.objects.filter(plot_id__in=plot_ids, date_recorded__gte=six_months_ago)
    monthly_ndvi = {}
    
    for i in range(5, -1, -1):
        d = today - timedelta(days=i*30)
        month_key = f"{d.year}-{d.month:02d}"
        month_label = calendar.month_abbr[d.month]
        monthly_ndvi[month_key] = {'label': month_label, 'total': 0, 'count': 0}
        
    for rec in ndvi_records:
        month_key = f"{rec.date_recorded.year}-{rec.date_recorded.month:02d}"
        if month_key in monthly_ndvi:
            monthly_ndvi[month_key]['total'] += float(rec.ndvi_value)
            monthly_ndvi[month_key]['count'] += 1
            
    ndvi_trend_labels = []
    ndvi_trend_data = []
    for key in sorted(monthly_ndvi.keys()): # chronological
        ndvi_trend_labels.append(monthly_ndvi[key]['label'])
        avg = monthly_ndvi[key]['total'] / monthly_ndvi[key]['count'] if monthly_ndvi[key]['count'] > 0 else 0
        ndvi_trend_data.append(round(avg, 2))

    # 2. Crop Health Distribution
    health_counts = {'Healthy': 0, 'Moderate': 0, 'Critical': 0}
    plot_data = []
    
    for plot in plots:
        latest_scout = plot.scouting_logs.order_by('-created_at').first()
        latest_ndvi = plot.ndvi_records.order_by('-date_recorded').first()
        
        health_status = 'Healthy'
        ndvi_display = 'N/A'
        date_display = 'No records'
        
        good_pct = 100
        mod_pct = 0
        attn_pct = 0
        
        if latest_ndvi:
            ndvi_display = str(latest_ndvi.ndvi_value)
            health_status = latest_ndvi.health_status
            date_display = str(latest_ndvi.date_recorded)
            good_pct = float(latest_ndvi.good_percent or 0)
            mod_pct = float(latest_ndvi.mod_percent or 0)
            attn_pct = float(latest_ndvi.attn_percent or 0)
            
        if latest_scout:
            if latest_scout.disease_presence:
                health_status = 'Critical'
            elif latest_scout.pest_presence or latest_scout.water_stress_symptoms or latest_scout.nutrient_deficiency:
                health_status = 'Moderate'
            
            if date_display == 'No records':
                date_display = str(latest_scout.created_at.date())
                
        if health_status in health_counts:
            health_counts[health_status] += 1
        
        lat = None
        lng = None
        if isinstance(plot.center_lt_ln, dict):
            lat = plot.center_lt_ln.get('lat', 0)
            lng = plot.center_lt_ln.get('lng', 0)
        elif plot.center_lt_ln:
            try:
                import json
                parsed = json.loads(plot.center_lt_ln.replace("'", '"'))
            except:
                try:
                    import ast
                    parsed = ast.literal_eval(plot.center_lt_ln)
                except:
                    parsed = None
                    
            if isinstance(parsed, dict):
                lat = parsed.get('lat', 0)
                lng = parsed.get('lng', 0)
            elif isinstance(parsed, list) and len(parsed) >= 2:
                lat = float(parsed[0])
                lng = float(parsed[1])
            elif isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], str) and ',' in parsed[0]:
                parts = parsed[0].split(',')
                lat = float(parts[0].strip())
                lng = float(parts[1].strip())
                
        if lat is None or lng is None:
            lat = plot.latitude
            lng = plot.longitude
            
        boundaries = plot.boundaries
        if isinstance(boundaries, str):
            try:
                import json
                boundaries = json.loads(boundaries)
            except:
                try:
                    import ast
                    boundaries = ast.literal_eval(boundaries)
                except:
                    pass
        
        plot_data.append({
            'plot_code': plot.plot_code,
            'farmer': plot.farmer.name if plot.farmer else '',
            'lat': lat,
            'lng': lng,
            'boundaries': boundaries,
            'ndvi_value': ndvi_display,
            'health_status': health_status,
            'date': date_display,
            'good_pct': good_pct,
            'mod_pct': mod_pct,
            'attn_pct': attn_pct
        })

    # 3. Scout Status
    scout_completed = Scout.objects.filter(plot_id__in=plot_ids, status='Completed').count()
    scout_pending = Scout.objects.filter(plot_id__in=plot_ids, status='Pending Assignment').count()
    scout_assigned = Scout.objects.filter(plot_id__in=plot_ids, status='Assigned').count()
    scout_status_data = [scout_completed, scout_pending, scout_assigned]

    # 4. Survey Completion
    surveys = Survey.objects.filter(plot_id__in=plot_ids)
    total_surveys = surveys.count()
    completed_surveys = sum(1 for s in surveys if s.status == 'Completed')
    
    if total_surveys > 0:
        survey_completed_perc = int((completed_surveys / total_surveys) * 100)
    else:
        survey_completed_perc = 100 if plot_ids else 0
    survey_completion_data = [survey_completed_perc, 100 - survey_completed_perc]

    import json
    context = {
        'plots': plot_data,
        'plot_data_json': json.dumps(plot_data),
        
        # Filter context
        'groups': groups,
        'factories': factories,
        'divisions': divisions,
        'sections': sections,
        'all_selected': all_selected,
        'all_factories_selected': selected_factory_id == 'all',
        'all_divisions_selected': selected_division_id == 'all',
        'all_sections_selected': selected_section_id == 'all',
        'active_factory_id': selected_factory_id,
        'user_factories': get_allowed_factories(request) if not is_superadmin else Factory.objects.all(),
        'hierarchy_data': hierarchy_data,
        
        # Chart Data
        'ndvi_trend_labels_json': json.dumps(ndvi_trend_labels),
        'ndvi_trend_data_json': json.dumps(ndvi_trend_data),
        'health_counts_json': json.dumps([health_counts['Healthy'], health_counts['Moderate'], health_counts['Critical']]),
        'scout_status_data_json': json.dumps(scout_status_data),
        'survey_completion_data_json': json.dumps(survey_completion_data),
        'survey_perc': survey_completed_perc
    }
    return render(request, 'ndvi_dashboard.html', context)


def scout_management(request):
    scouts = Scout.objects.all().order_by('-created_at')
    officers = Officer.objects.all()
    
    total_scouts = scouts.count()
    pending_scouts = scouts.filter(status='Pending Assignment').count()
    assigned_scouts = scouts.filter(status='Assigned').count()
    completed_scouts = scouts.filter(status='Completed').count()
    critical_alerts = scouts.filter(priority='High').count()

    context = {
        'scouts': scouts,
        'officers': officers,
        'total_scouts': total_scouts,
        'pending_scouts': pending_scouts,
        'assigned_scouts': assigned_scouts,
        'completed_scouts': completed_scouts,
        'critical_alerts': critical_alerts,
    }
    return render(request, 'scout_management.html', context)

def assign_scout(request):
    if request.method == 'POST':
        scout_id = request.POST.get('scout_id')
        officer_id = request.POST.get('officer_id')
        notes = request.POST.get('notes', '')

        try:
            scout = Scout.objects.get(id=scout_id)
            officer = Officer.objects.get(id=officer_id)
            
            # Create or update assignment
            assignment, created = ScoutAssignment.objects.update_or_create(
                scout=scout,
                defaults={'officer': officer, 'notes': notes}
            )
            
            # Update Scout status
            scout.status = 'Assigned'
            scout.save()
            
            messages.success(request, f'Scout {scout.scout_id} assigned to {officer.name}.')
        except Exception as e:
            messages.error(request, f'Error assigning scout: {str(e)}')
            
    return redirect('scout_management')



