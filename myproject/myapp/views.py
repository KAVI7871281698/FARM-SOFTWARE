from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .models import Role, Officer, Section, Village, Farmer, Variety, Crop, Group, Factory, Division, WorkAssign, Plot, SoilType, ScoutingLog, Survey, SurveyResult,ScoutResult
from django.core.paginator import Paginator

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

def scout_management(request):
    scouts = Scout.objects.select_related('plot', 'plot__farmer').order_by('-created_at')
    officers = Officer.objects.select_related('role', 'division', 'group', 'factory', 'section').all()
    
    total_scouts = scouts.count()
    pending_scouts = scouts.filter(status='Pending Assignment').count()
    assigned_scouts = scouts.filter(status='Assigned').count()
    completed_scouts = scouts.filter(status='Completed').count()
    critical_alerts = scouts.filter(priority='High').count()

    divisions = Division.objects.all()
    
    paginator = Paginator(scouts, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'scouts': page_obj,
        'officers': officers,
        'divisions': divisions,
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

            ScoutAssignment.objects.create(
                scout=scout,
                officer=officer,
                notes=notes
            )
            scout.status = 'Assigned'
            scout.save()

            messages.success(request, f'Scout successfully assigned to {officer.name}.')
        except (Scout.DoesNotExist, Officer.DoesNotExist):
            messages.error(request, 'Invalid scout or officer selection.')

    return redirect('scout_management')

def get_sections_by_division(request):
    division_id = request.GET.get('division_id')
    sections = Section.objects.filter(division_id=division_id).values('id', 'section_name')
    return JsonResponse(list(sections), safe=False)

def get_villages_by_section(request):
    section_id = request.GET.get('section_id')
    villages = Village.objects.filter(section_id=section_id).values('id', 'village_name')
    return JsonResponse(list(villages), safe=False)

def get_plots_by_village(request):
    village_id = request.GET.get('village_id')
    plots = Plot.objects.filter(village_id=village_id).select_related('farmer').values('id', 'plot_code', 'farmer__name')
    return JsonResponse(list(plots), safe=False)

def create_manual_scout(request):
    if request.method == 'POST':
        plot_id = request.POST.get('plot_id')
        priority = request.POST.get('priority', 'Medium')
        alert_reason = request.POST.get('alert_reason', 'Manual Scout Created')

        if plot_id:
            plot = Plot.objects.filter(id=plot_id).first()
            if plot:
                scout = Scout.objects.create(
                    plot=plot,
                    alert_reason=alert_reason,
                    priority=priority,
                    status='Pending Assignment',
                    ndvi_value=None
                )

                division_id = None
                if plot.division:
                    division_id = plot.division.id
                elif plot.farmer and plot.farmer.division:
                    division_id = plot.farmer.division.id
                
                if division_id:
                    officers = Officer.objects.select_related('role', 'division', 'group', 'factory', 'section').all()
                    assigned_officer = None
                    for officer in officers:
                        if officer.division_ids:
                            try:
                                div_ids_str = str(officer.division_ids).replace("'", '"')
                                div_ids = json.loads(div_ids_str)
                                if str(division_id) in [str(d).strip() for d in div_ids]:
                                    assigned_officer = officer
                                    break
                            except:
                                if str(division_id) in str(officer.division_ids):
                                    assigned_officer = officer
                                    break
                    
                    if assigned_officer:
                        ScoutAssignment.objects.create(
                            scout=scout,
                            officer=assigned_officer,
                            notes="Auto-assigned manual scout."
                        )
                        scout.status = 'Assigned'
                        scout.save()
                        messages.success(request, f"Manual Scout created and automatically assigned to {assigned_officer.name}.")
                    else:
                        messages.warning(request, "Manual Scout created but no officer found for this division.")
                else:
                    messages.warning(request, "Manual Scout created but plot has no division to auto-assign.")

    return redirect('scout_management')

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
    from django.db.models import Avg, Q, OuterRef, Subquery
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

    from django.db.models import Count
    plot_stats = plots_qs.aggregate(
        total=Count('id'),
        mapped=Count('id', filter=Q(status='Mapped') | Q(status='mapped') | (Q(boundaries__isnull=False) & ~Q(boundaries='')))
    )
    total_plots = plot_stats['total']
    mapped = plot_stats['mapped']
    unmapped = total_plots - mapped

    ndvi_stats = NDVIRecord.objects.filter(plot__in=plots_qs).aggregate(
        avg_val=Avg('ndvi_value'),
        need_attention=Count('plot', filter=Q(health_status='Critical'), distinct=True)
    )
    avg_ndvi = round(ndvi_stats['avg_val'], 2) if ndvi_stats['avg_val'] else 0.0
    need_attention = ndvi_stats['need_attention']

    scout_stats_agg = Scout.objects.filter(plot__in=plots_qs).aggregate(
        overdue=Count('id', filter=Q(status='Pending Assignment')),
        completed=Count('id', filter=Q(status='Completed')),
        assigned=Count('id', filter=Q(status='Assigned'))
    )
    overdue_scouts = scout_stats_agg['overdue']
    scout_completed = scout_stats_agg['completed']
    scout_pending = scout_stats_agg['overdue']
    scout_assigned = scout_stats_agg['assigned']
    scout_status_data = [scout_completed, scout_pending, scout_assigned]

    damage_reports = ScoutSurveyReport.objects.filter(scout__plot__in=plots_qs).exclude(pest_details='', disease_details='').count()

    # Charts Data
    from datetime import date, timedelta
    import calendar
    today = date.today()
    six_months_ago = today.replace(day=1) - timedelta(days=5*30)
    six_months_ago = six_months_ago.replace(day=1)
    
    ndvi_records_values = NDVIRecord.objects.filter(plot__in=plots_qs, date_recorded__gte=six_months_ago).values('date_recorded', 'ndvi_value', 'health_status', 'stage')
    
    monthly_ndvi = {}
    for i in range(5, -1, -1):
        d = today - timedelta(days=i*30)
        month_key = f"{d.year}-{d.month:02d}"
        month_label = calendar.month_abbr[d.month]
        monthly_ndvi[month_key] = {'label': month_label, 'total': 0, 'count': 0}
        
    unique_dates = set()
    for rec in ndvi_records_values:
        d = rec['date_recorded']
        unique_dates.add(d)
        month_key = f"{d.year}-{d.month:02d}"
        if month_key in monthly_ndvi:
            monthly_ndvi[month_key]['total'] += float(rec['ndvi_value'])
            monthly_ndvi[month_key]['count'] += 1
            
    ndvi_trend_labels = []
    ndvi_trend_data = []
    for key in sorted(monthly_ndvi.keys()):
        ndvi_trend_labels.append(monthly_ndvi[key]['label'])
        avg_val = monthly_ndvi[key]['total'] / monthly_ndvi[key]['count'] if monthly_ndvi[key]['count'] > 0 else 0
        ndvi_trend_data.append(round(avg_val, 2))

    # Fortnightly trend for Health and Stage
    unique_dates = sorted(list(unique_dates))
    unique_dates = unique_dates[-15:] if len(unique_dates) > 15 else unique_dates
    
    ht_labels = [d.strftime('%Y-%m-%d') for d in unique_dates]
    
    ht_health_data = { 'Good': [0]*len(unique_dates), 'Moderate': [0]*len(unique_dates), 'Need Attention': [0]*len(unique_dates) }
    ht_stage_data = { 'Germination': [0]*len(unique_dates), 'Early Tiller': [0]*len(unique_dates), 'Tillering': [0]*len(unique_dates), 'Grand growth': [0]*len(unique_dates), 'Maturity': [0]*len(unique_dates) }
    
    date_to_index = {d: i for i, d in enumerate(unique_dates)}
    
    for rec in ndvi_records_values:
        d = rec['date_recorded']
        if d in date_to_index:
            idx = date_to_index[d]
            h = rec['health_status']
            if h == 'Good': ht_health_data['Good'][idx] += 1
            elif h == 'Moderate': ht_health_data['Moderate'][idx] += 1
            elif h == 'Need Attention': ht_health_data['Need Attention'][idx] += 1
            
            s = rec['stage']
            if s in ht_stage_data:
                ht_stage_data[s][idx] += 1

    latest_scouts = ScoutingLog.objects.filter(plot__in=plots_qs).order_by('plot', '-created_at').distinct('plot')
    latest_ndvis = NDVIRecord.objects.filter(plot__in=plots_qs).order_by('plot', '-date_recorded').distinct('plot')
    
    scout_dict = {s.plot_id: s for s in latest_scouts}
    ndvi_dict = {n.plot_id: n for n in latest_ndvis}
    
    health_counts = {'Healthy': 0, 'Moderate': 0, 'Critical': 0}
    for p_id in plots_qs.values_list('id', flat=True):
        health_status = 'Healthy'
        latest_ndvi = ndvi_dict.get(p_id)
        latest_scout = scout_dict.get(p_id)
        
        if latest_ndvi:
            health_status = latest_ndvi.health_status
        if latest_scout:
            if latest_scout.disease_presence:
                health_status = 'Critical'
            elif latest_scout.pest_presence or latest_scout.water_stress_symptoms or latest_scout.nutrient_deficiency:
                health_status = 'Moderate'
            
        if health_status in health_counts:
            health_counts[health_status] += 1

    surveys = Survey.objects.filter(plot__in=plots_qs).prefetch_related('results')
    total_surveys = surveys.count()
    completed_surveys = 0
    for s in surveys:
        completed_count = len(set(r.survey_date for r in s.results.all() if r.survey_status == 'Completed'))
        perc = min(int((completed_count / s.number_of_days) * 100), 100) if s.number_of_days else 0
        if perc == 100:
            completed_surveys += 1
            
    if total_surveys > 0:
        survey_completed_perc = int((completed_surveys / total_surveys) * 100)
    else:
        survey_completed_perc = 100 if total_plots > 0 else 0
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
        
    paginator = Paginator(officers_list, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'officers.html', {'officers': page_obj})

from django.db.models import Q

def field_intelligence(request):
    base_plots = Plot.objects.filter(
        Q(center_lt_ln__isnull=False) | 
        (Q(latitude__isnull=False) & Q(longitude__isnull=False))
    ).select_related('division', 'section', 'village', 'farmer', 'soil_type')
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
    logs = filter_by_factory(ScoutingLog.objects.all(), 'plot__farmer__section__division__factory_name_id', request).select_related(
        'group', 'factory', 'division', 'section', 'village', 'plot', 'officer'
    ).order_by('-created_at')
    
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'scouting.html', {'plots': plots, 'logs': page_obj})

def scout_logs(request):
    logs = filter_by_factory(ScoutingLog.objects.all(), 'plot__farmer__section__division__factory_name_id', request).select_related(
        'group', 'factory', 'division', 'section', 'village', 'plot', 'officer'
    ).order_by('-created_at')
    
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'scout_logs.html', {'logs': page_obj})

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
    paginator = Paginator(farmers_list, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'users.html', {'farmers': page_obj})

def villages(request):
    villages_list = filter_by_factory(Village.objects.all(), 'section__division__factory_name_id', request)
    paginator = Paginator(villages_list, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'villages.html', {'villages': page_obj})

def sections(request):
    sections_list = filter_by_factory(Section.objects.all(), 'division__factory_name_id', request)
    paginator = Paginator(sections_list, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'sections.html', {'sections': page_obj})

def varieties(request):
    varieties_list = Variety.objects.all()
    paginator = Paginator(varieties_list, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'varieties.html', {'varieties': page_obj})

def plots(request):
    plots_list = filter_by_factory(Plot.objects.all(), 'farmer__section__division__factory_name_id', request).select_related('farmer', 'crop_type', 'variety', 'soil_type')
    paginator = Paginator(plots_list, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'plots.html', {'plots': page_obj})

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
    
    paginator = Paginator(surveys_list, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'surveys': page_obj,
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
        if not division and section and section.division:
            division = section.division.name
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

def import_officers(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        task_id = request.POST.get('task_id')
        if task_id:
            from django.core.cache import cache
            cache.set(task_id, 0, timeout=300)
            
        excel_file = request.FILES['excel_file']
        try:
            import pandas as pd
            if excel_file.name.endswith('.csv'):
                df = pd.read_csv(excel_file)
            else:
                df = pd.read_excel(excel_file)
            df.columns = df.columns.astype(str).str.strip().str.lower()
            
            # DEBUG: Print columns to the terminal
            print("\n" + "="*50)
            print("IMPORTED FILE COLUMNS:")
            print(df.columns.tolist())
            print("="*50 + "\n")
            
            imported_count = 0
            total_rows = len(df)
            
            for index, row in df.iterrows():
                if task_id and total_rows > 0:
                    from django.core.cache import cache
                    percentage = int(((index + 1) / total_rows) * 100)
                    cache.set(task_id, percentage, timeout=300)
                    
                name = str(row.get('name', '')).strip()
                mobile = str(row.get('phone', row.get('mobile', ''))).strip()
                employee_code = str(row.get('employee_code', '')).strip()
                original_id = str(row.get('id', '')).strip()
                email = str(row.get('email', '')).strip()
                
                # If email is missing, generate a dummy one as it's required by the model
                if not email or email == 'nan':
                    email = f"{employee_code}@farmsignals.com" if employee_code and employee_code != 'nan' else f"{mobile}@farmsignals.com"
                
                password = str(row.get('password', 'default123')).strip()
                role_name = str(row.get('role', '')).strip()
                group_name = str(row.get('group', '')).strip()
                factory_names = str(row.get('factory_code', row.get('factories', ''))).strip()
                division_names = str(row.get('division_code', row.get('divisions', ''))).strip()
                section_names = str(row.get('sections', '')).strip()
                
                if name and name != 'nan' and mobile and mobile != 'nan':
                    role = Role.objects.filter(name__iexact=role_name).first() if role_name and role_name != 'nan' else None
                    group = Group.objects.filter(name__iexact=group_name).first() if group_name and group_name != 'nan' else None
                    
                    try:
                        officer, created = Officer.objects.get_or_create(mobile=mobile, defaults={
                            'name': name,
                            'email': email,
                            'user_id': employee_code if employee_code != 'nan' else "",
                            'device_id': original_id if original_id != 'nan' else "",
                            'password': password if password and password != 'nan' else 'default123',
                            'role': role,
                            'role_name': role.name if role else role_name if role_name != 'nan' else "",
                            'group': group,
                            'group_name': group.name if group else group_name if group_name != 'nan' else "",
                            'factory_names': factory_names if factory_names != 'nan' else "",
                            'division_names': division_names if division_names != 'nan' else "",
                            'section_names': section_names if section_names != 'nan' else "",
                        })
                        if not created:
                            officer.name = name
                            if email: officer.email = email
                            if employee_code and employee_code != 'nan': officer.user_id = employee_code
                            if original_id and original_id != 'nan': officer.device_id = original_id
                            officer.role = role
                            officer.role_name = role.name if role else role_name if role_name != 'nan' else ""
                            officer.group = group
                            officer.group_name = group.name if group else group_name if group_name != 'nan' else ""
                            if password and password != 'nan': officer.password = password
                            if factory_names and factory_names != 'nan': officer.factory_names = factory_names
                            if division_names and division_names != 'nan': officer.division_names = division_names
                            if section_names and section_names != 'nan': officer.section_names = section_names
                            officer.save()
                        imported_count += 1
                    except Exception as e:
                        print(f"Error importing officer {mobile}: {e}")
            
            if imported_count == 0:
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'status': 'error', 'message': 'No officers imported. Please check the file format.'})
                messages.error(request, f'No officers imported. Please check the file format.')
            else:
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'status': 'success', 'message': f'{imported_count} Officers imported successfully!', 'imported_count': imported_count})
                messages.success(request, f'{imported_count} Officers imported successfully!')
        except Exception as e:
            if is_ajax:
                from django.http import JsonResponse
                return JsonResponse({'status': 'error', 'message': f'Error importing officers: {str(e)}'})
            messages.error(request, f'Error importing officers: {str(e)}')
    return redirect('officers')

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
            
    plots = Plot.objects.select_related('farmer', 'division', 'section', 'village', 'crop_type', 'variety', 'soil_type', 'group', 'factory', 'officer').all()
    officers = Officer.objects.select_related('role', 'division', 'group', 'factory', 'section').all()
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
        
    plots = Plot.objects.select_related('farmer', 'division', 'section', 'village', 'crop_type', 'variety', 'soil_type', 'group', 'factory', 'officer').all()
    officers = Officer.objects.select_related('role', 'division', 'group', 'factory', 'section').all()
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
            if not division and section and section.division:
                division = section.division.name
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
        village.division = request.POST.get('division') or (section.division.name if section and section.division else '')
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

def import_work_assigns(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        task_id = request.POST.get('task_id')
        if task_id:
            from django.core.cache import cache
            cache.set(task_id, 0, timeout=300)
            
        excel_file = request.FILES['excel_file']
        try:
            import pandas as pd
            if excel_file.name.endswith('.csv'):
                df = pd.read_csv(excel_file)
            else:
                df = pd.read_excel(excel_file)
            df.columns = df.columns.astype(str).str.strip().str.lower()
            
            # DEBUG: Print columns to the terminal
            print("\n" + "="*50)
            print("IMPORTED WORK ASSIGN FILE COLUMNS:")
            print(df.columns.tolist())
            print("="*50 + "\n")
            
            imported_count = 0
            total_rows = len(df)
            
            error_messages = []
            
            for index, row in df.iterrows():
                if task_id and total_rows > 0:
                    from django.core.cache import cache
                    percentage = int(((index + 1) / total_rows) * 100)
                    cache.set(task_id, percentage, timeout=300)
                    
                # Basic mapping based on user's exact columns
                officer_id_raw = str(row.get('officer_id', '')).strip()
                if officer_id_raw.endswith('.0'):
                    officer_id_raw = officer_id_raw[:-2]
                    
                division_code = str(row.get('division_code', '')).strip()
                status = str(row.get('status', 'active')).strip()
                
                if officer_id_raw and officer_id_raw != 'nan':
                    # Try finding officer by PK id, or user_id, or mobile
                    officer = None
                    if officer_id_raw.isdigit():
                        officer = Officer.objects.filter(id=int(officer_id_raw)).first()
                    
                    if not officer:
                        from django.db.models import Q
                        officer = Officer.objects.filter(Q(device_id=officer_id_raw) | Q(user_id=officer_id_raw) | Q(mobile=officer_id_raw)).first()
                    
                    if not officer:
                        error_messages.append(f"Row {index+1}: Officer not found for ID '{officer_id_raw}'")
                        continue
                        
                    try:
                        assign, created = WorkAssign.objects.get_or_create(
                            officer=officer,
                            division=division_code if division_code != 'nan' else '',
                            defaults={
                                'status': status if status != 'nan' else 'active'
                            }
                        )
                        if not created:
                            if status and status != 'nan': assign.status = status
                            assign.save()
                        imported_count += 1
                    except Exception as e:
                        error_messages.append(f"Row {index+1}: {str(e)}")
            
            if imported_count == 0 and not error_messages:
                err_msg = 'No work assignments imported. Please check the file format.'
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'status': 'error', 'message': err_msg})
                messages.error(request, err_msg)
            else:
                success_msg = f'{imported_count} imported successfully.'
                if error_messages:
                    if imported_count == 0:
                        success_msg = f"0 imported. Skipped {len(error_messages)} rows (e.g., {error_messages[0]})"
                    else:
                        success_msg += f" Skipped {len(error_messages)} rows."
                        
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({'status': 'success', 'message': success_msg, 'imported_count': imported_count})
                messages.success(request, success_msg)
        except Exception as e:
            if is_ajax:
                from django.http import JsonResponse
                return JsonResponse({'status': 'error', 'message': f'Error importing work assignments: {str(e)}'})
            messages.error(request, f'Error importing work assignments: {str(e)}')
    return redirect('work_assigns')

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
    sections = Section.objects.select_related('division').all().select_related('division')
    villages = Village.objects.select_related('division', 'section').all().select_related('section')
    officers = Officer.objects.select_related('role', 'division', 'group', 'factory', 'section').all()

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
    sections = Section.objects.select_related('division').all().select_related('division')
    villages = Village.objects.select_related('division', 'section').all().select_related('section')
    officers = Officer.objects.select_related('role', 'division', 'group', 'factory', 'section').all()

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
    base_plots = Plot.objects.select_related(
        'division', 'section', 'village', 'farmer', 'soil_type'
    ).filter(
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
    farmers = Farmer.objects.select_related('division', 'section', 'village', 'group', 'factory').all()
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
    from django.db.models import Prefetch
    plots_query = Plot.objects.filter(Q(center_lt_ln__isnull=False) | Q(boundaries__isnull=False)).select_related('farmer').prefetch_related(
        Prefetch('scouting_logs', queryset=ScoutingLog.objects.order_by('-created_at')),
        Prefetch('ndvi_records', queryset=NDVIRecord.objects.order_by('-date_recorded'))
    ).distinct()
    
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
        scouts = list(plot.scouting_logs.all())
        latest_scout = scouts[0] if scouts else None
        ndvis = list(plot.ndvi_records.all())
        latest_ndvi = ndvis[0] if ndvis else None
        
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
        if isinstance(plot.center_lt_ln, list) and len(plot.center_lt_ln) >= 2:
            lat = float(plot.center_lt_ln[0])
            lng = float(plot.center_lt_ln[1])
        elif isinstance(plot.center_lt_ln, dict):
            lat = float(plot.center_lt_ln.get('lat', 0))
            lng = float(plot.center_lt_ln.get('lng', 0))
        elif plot.center_lt_ln:
            try:
                import json
                if isinstance(plot.center_lt_ln, str):
                    parsed = json.loads(plot.center_lt_ln.replace("'", '"'))
                else:
                    parsed = plot.center_lt_ln
                if isinstance(parsed, list) and len(parsed) >= 2:
                    lat = float(parsed[0])
                    lng = float(parsed[1])
                elif isinstance(parsed, dict):
                    lat = float(parsed.get('lat', 0))
                    lng = float(parsed.get('lng', 0))
            except:
                pass
                
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

def compare_ndvi_data(request):
    from django.http import JsonResponse
    from django.db.models import Avg, F
    
    level = request.GET.get('level', 'division')
    
    qs = NDVIRecord.objects.all()
    
    if level == 'factory':
        qs = qs.annotate(name=F('plot__factory_name'))
    elif level == 'division':
        qs = qs.annotate(name=F('plot__division_name'))
    elif level == 'section':
        qs = qs.annotate(name=F('plot__section_name'))
    elif level == 'village':
        qs = qs.annotate(name=F('plot__village_name'))
    else:
        return JsonResponse({'error': 'Invalid level'}, status=400)
        
    data = qs.values('name').annotate(
        avg_ndvi=Avg('ndvi_mean')

    ).exclude(name__isnull=True).exclude(name='').order_by('name')
    
    labels = []
    avg_ndvis = []
    
    for item in data:
        labels.append(item['name'])
        avg_ndvis.append(round(float(item['avg_ndvi'] or 0), 4))
        
    return JsonResponse({
        'labels': labels,
        'avg_ndvis': avg_ndvis
    })

def scout_result_view(request):
    results = ScoutResult.objects.all().order_by('-created_at')
    return render(request, 'scout_result.html', {'results': results})

import pandas as pd
from django.contrib import messages

def import_groups(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        try:
            if excel_file.name.endswith('.csv'):
                df = pd.read_csv(excel_file)
            else:
                df = pd.read_excel(excel_file)
            df.columns = df.columns.str.strip().str.lower()
            for index, row in df.iterrows():
                code = str(row.get('code', row.get('group code', '')))
                name = str(row.get('name', row.get('group name', '')))
                if name and name != 'nan':
                    group, created = Group.objects.get_or_create(name=name, defaults={'code': code if code != 'nan' else ''})
                    if not created and code and code != 'nan':
                        group.code = code
                        group.save()
            messages.success(request, 'Groups imported successfully!')
        except Exception as e:
            messages.error(request, f'Error importing groups: {str(e)}')
    return redirect('groups')

def import_factories(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        try:
            if excel_file.name.endswith('.csv'):
                df = pd.read_csv(excel_file)
            else:
                df = pd.read_excel(excel_file)
            df.columns = df.columns.astype(str).str.strip().str.lower()
            print(f"DEBUG: Loaded file. Columns found: {list(df.columns)}")
            
            imported_count = 0
            for index, row in df.iterrows():
                group_name = str(row.get('group_name', row.get('group name', row.get('group', '')))).strip()
                group_code_col = str(row.get('group_code', row.get('group code', ''))).strip()
                
                code = str(row.get('code', row.get('factory code', ''))).strip()
                name = str(row.get('name', row.get('factory name', row.get('factory', '')))).strip()
                location = str(row.get('location', row.get('location (lat/long)', row.get('location_latlong', '')))).strip()
                capacity = str(row.get('crushing_capacity', row.get('crushing capacity', row.get('capacity', '')))).strip()
                
                has_group = (group_name and group_name != 'nan') or (group_code_col and group_code_col != 'nan')
                if name and name != 'nan' and has_group:
                    group = None
                    if group_name and group_name != 'nan':
                        group = Group.objects.filter(name__iexact=group_name).first()
                        if not group:
                            group = Group.objects.filter(code__iexact=group_name).first()
                    
                    if not group and group_code_col and group_code_col != 'nan':
                        group = Group.objects.filter(code__iexact=group_code_col).first()
                        if not group:
                            group = Group.objects.filter(name__iexact=group_code_col).first()
                            
                    if group:
                        factory, created = Factory.objects.get_or_create(name=name, group=group, defaults={
                            'code': code if code != 'nan' else '',
                            'location_LatLong': location if location != 'nan' else '',
                            'crushing_capacity': capacity if capacity != 'nan' else ''
                        })
                        if not created:
                            factory.code = code if code != 'nan' else factory.code
                            factory.location_LatLong = location if location != 'nan' else factory.location_LatLong
                            factory.crushing_capacity = capacity if capacity != 'nan' else factory.crushing_capacity
                            factory.save()
                        imported_count += 1
            
            if imported_count == 0:
                print(f"DEBUG: No factories imported. Columns: {list(df.columns)}")
                messages.error(request, f'No factories imported. Columns found: {list(df.columns)}. Make sure Group Name and Factory Name are present and Groups already exist.')
            else:
                print(f"DEBUG: {imported_count} factories imported successfully!")
                messages.success(request, f'{imported_count} Factories imported successfully!')
        except Exception as e:
            print(f"DEBUG EXCEPTION: {str(e)}")
            messages.error(request, f'Error importing factories: {str(e)}')
    return redirect('factories')

def import_divisions(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        try:
            if excel_file.name.endswith('.csv'):
                df = pd.read_csv(excel_file)
            else:
                df = pd.read_excel(excel_file)
            df.columns = df.columns.astype(str).str.strip().str.lower()
            print(f"DEBUG: Loaded file. Columns found: {list(df.columns)}")
            
            imported_count = 0
            for index, row in df.iterrows():
                code = str(row.get('code', row.get('division code', ''))).strip()
                name = str(row.get('name', row.get('division name', ''))).strip()
                factory_code_col = str(row.get('factory_code', row.get('factory code', ''))).strip()
                
                if name and name != 'nan':
                    factory = Factory.objects.filter(code__iexact=factory_code_col).first() if factory_code_col and factory_code_col != 'nan' else None
                    if factory:
                        div, created = Division.objects.get_or_create(name=name, factory_name=factory, defaults={'code': code if code != 'nan' else ''})
                        if not created and code and code != 'nan':
                            div.code = code
                            div.save()
                        imported_count += 1
            if imported_count == 0:
                print(f"DEBUG: No divisions imported. Columns: {list(df.columns)}"); messages.error(request, f'No divisions imported. Columns found: {list(df.columns)}')
            else:
                messages.success(request, f'{imported_count} Divisions imported successfully!')
        except Exception as e:
            print(f"DEBUG Error importing divisions: {str(e)}"); messages.error(request, f'Error importing divisions: {str(e)}')
    return redirect('divisions')

def import_sections(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        try:
            if excel_file.name.endswith('.csv'):
                df = pd.read_csv(excel_file)
            else:
                df = pd.read_excel(excel_file)
            df.columns = df.columns.astype(str).str.strip().str.lower()
            print(f"DEBUG: Loaded file. Columns found: {list(df.columns)}")
            
            imported_count = 0
            for index, row in df.iterrows():
                code = str(row.get('section_code', row.get('section code', row.get('code', '')))).strip()
                name = str(row.get('section_name', row.get('section name', row.get('name', '')))).strip()
                desc = str(row.get('description', '')).strip()
                division_code = str(row.get('division_code', row.get('division code', ''))).strip()
                
                if name and name != 'nan':
                    division = Division.objects.filter(code__iexact=division_code).first() if division_code and division_code != 'nan' else None
                    if division:
                        sec, created = Section.objects.get_or_create(section_name=name, division=division, defaults={
                            'section_code': code if code != 'nan' else '',
                            'description': desc if desc != 'nan' else ''
                        })
                        if not created:
                            if code and code != 'nan': sec.section_code = code
                            if desc and desc != 'nan': sec.description = desc
                            sec.save()
                        imported_count += 1
            if imported_count == 0:
                print(f"DEBUG: No sections imported. Columns: {list(df.columns)}"); messages.error(request, f'No sections imported. Columns found: {list(df.columns)}')
            else:
                messages.success(request, f'{imported_count} Sections imported successfully!')
        except Exception as e:
            print(f"DEBUG Error importing sections: {str(e)}"); messages.error(request, f'Error importing sections: {str(e)}')
    return redirect('sections')

def import_villages(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        try:
            if excel_file.name.endswith('.csv'):
                df = pd.read_csv(excel_file)
            else:
                df = pd.read_excel(excel_file)
            df.columns = df.columns.astype(str).str.strip().str.lower()
            print(f"DEBUG: Loaded file. Columns found: {list(df.columns)}")
            
            imported_count = 0
            for index, row in df.iterrows():
                code = str(row.get('village_code', row.get('village code', row.get('code', '')))).strip()
                name = str(row.get('village_name', row.get('village name', row.get('name', '')))).strip()
                div_name = str(row.get('division', '')).strip()
                taluk = str(row.get('taluk', '')).strip()
                district = str(row.get('district', '')).strip()
                state = str(row.get('state', '')).strip()
                section_code = str(row.get('section_code', row.get('section code', row.get('code', '')))).strip()
                
                if name and name != 'nan':
                    section = Section.objects.filter(section_code__iexact=section_code).first() if section_code and section_code != 'nan' else None
                    if section:
                        vil, created = Village.objects.get_or_create(village_name=name, section=section, defaults={
                            'village_code': code if code != 'nan' else '',
                            'division': div_name if div_name and div_name != 'nan' else (section.division.name if section and section.division else ''),
                            'taluk': taluk if taluk != 'nan' else '',
                            'district': district if district != 'nan' else '',
                            'state': state if state != 'nan' else ''
                        })
                        if not created:
                            if code and code != 'nan': vil.village_code = code
                            if div_name and div_name != 'nan':
                                vil.division = div_name
                            elif section and section.division:
                                vil.division = section.division.name
                            if taluk and taluk != 'nan': vil.taluk = taluk
                            if district and district != 'nan': vil.district = district
                            if state and state != 'nan': vil.state = state
                            vil.save()
                        imported_count += 1
            if imported_count == 0:
                print(f"DEBUG: No villages imported. Columns: {list(df.columns)}"); messages.error(request, f'No villages imported. Columns found: {list(df.columns)}')
            else:
                messages.success(request, f'{imported_count} Villages imported successfully!')
        except Exception as e:
            print(f"DEBUG Error importing villages: {str(e)}"); messages.error(request, f'Error importing villages: {str(e)}')
    return redirect('villages')

from django.core.cache import cache

def import_farmers(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        task_id = request.POST.get('task_id')
        if task_id:
            cache.set(task_id, 0, timeout=300)
            
        excel_file = request.FILES['excel_file']
        try:
            if excel_file.name.endswith('.csv'):
                df = pd.read_csv(excel_file)
            else:
                df = pd.read_excel(excel_file)
            df.columns = df.columns.astype(str).str.strip().str.lower()
            print(f"DEBUG: Loaded file. Columns found: {list(df.columns)}")
            
            imported_count = 0
            total_rows = len(df)
            
            for index, row in df.iterrows():
                # Update progress
                if task_id and total_rows > 0:
                    percentage = int(((index + 1) / total_rows) * 100)
                    cache.set(task_id, percentage, timeout=300)

                code = str(row.get('farmer_code', row.get('farmer code', row.get('code', '')))).strip()
                name = str(row.get('name', row.get('farmer name', ''))).strip()
                father = str(row.get('father_name', row.get('father name', ''))).strip()
                phone = str(row.get('phone', row.get('phone number', ''))).strip()
                
                sec_code = str(row.get('section_code', row.get('section code', row.get('code', '')))).strip()
                vil_code = str(row.get('village_code', row.get('village code', row.get('code', '')))).strip()
                group_code = str(row.get('group_code', row.get('group code', ''))).strip()
                factory_code = str(row.get('factory_code', row.get('factory code', ''))).strip()
                
                if name and name != 'nan':
                    sec_val = sec_code if sec_code and sec_code != 'nan' else None
                    vil_val = vil_code if vil_code and vil_code != 'nan' else None
                    group_val = group_code if group_code and group_code != 'nan' else None
                    factory_val = factory_code if factory_code and factory_code != 'nan' else None

                    section = Section.objects.filter(section_code__iexact=sec_val).first() if sec_val else None
                    village = Village.objects.filter(village_code__iexact=vil_val).first() if vil_val else None
                    group = Group.objects.filter(code__iexact=group_val).first() if group_val else None
                    factory = Factory.objects.filter(code__iexact=factory_val).first() if factory_val else None

                    if village and not section:
                        section = village.section

                    if section:
                        if not factory and hasattr(section, 'division') and section.division and hasattr(section.division, 'factory_name') and section.division.factory_name:
                            factory = section.division.factory_name
                        if not group and factory and hasattr(factory, 'group') and factory.group:
                            group = factory.group

                    division_name = None
                    if section and hasattr(section, 'division') and section.division:
                        division_name = section.division.name
                    elif village and hasattr(village, 'division') and village.division:
                        division_name = village.division

                    # We can proceed if we have at least name, we don't strictly reject if village is missing, or we can just require village. 
                    # Previous code was `if section and village:`. We will keep it but now section can be derived from village.
                    if village:
                        frm, created = Farmer.objects.get_or_create(name=name, phone=phone if phone != 'nan' else '', defaults={
                            'farmer_code': code if code != 'nan' else '',
                            'father_name': father if father != 'nan' else '',
                            'section': section,
                            'village': village,
                            'division': division_name,
                            'group': group,
                            'group_name': group.name if group else '',
                            'factory': factory,
                            'factory_name': factory.name if factory else ''
                        })
                        if not created:
                            if code and code != 'nan': frm.farmer_code = code
                            if father and father != 'nan': frm.father_name = father
                            if section: frm.section = section
                            if village: frm.village = village
                            if division_name: frm.division = division_name
                            if group:
                                frm.group = group
                                frm.group_name = group.name
                            if factory:
                                frm.factory = factory
                                frm.factory_name = factory.name
                            frm.save()
                        imported_count += 1
            if imported_count == 0:
                print(f"DEBUG: No farmers imported. Columns: {list(df.columns)}")
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': f'No farmers imported. Columns found: {list(df.columns)}'})
                messages.error(request, f'No farmers imported. Columns found: {list(df.columns)}')
            else:
                if is_ajax:
                    return JsonResponse({'status': 'success', 'message': f'{imported_count} Farmers imported successfully!', 'imported_count': imported_count})
                messages.success(request, f'{imported_count} Farmers imported successfully!')
        except Exception as e:
            print(f"DEBUG Error importing farmers: {str(e)}")
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': f'Error importing farmers: {str(e)}'})
            messages.error(request, f'Error importing farmers: {str(e)}')
    return redirect('users')

def import_progress(request):
    task_id = request.GET.get('task_id')
    progress = 0
    if task_id:
        from django.core.cache import cache
        progress = cache.get(task_id, 0)
    return JsonResponse({'progress': progress})

import json
from django.apps import apps
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

@require_POST
def bulk_delete(request):
    if not request.session.get('user_id'):
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)
    
    try:
        data = json.loads(request.body)
        model_name = data.get('model')
        action = data.get('action')
        ids = data.get('ids', [])

        if not model_name:
            return JsonResponse({'status': 'error', 'message': 'Model name is required'}, status=400)
            
        model = apps.get_model('myapp', model_name)
        
        if action == 'delete_all':
            # Optionally check if user is superadmin
            if request.session.get('role_id') != 1:
                return JsonResponse({'status': 'error', 'message': 'Only superadmins can delete all records'}, status=403)
            deleted_count, _ = model.objects.all().delete()
            return JsonResponse({'status': 'success', 'message': f'Successfully deleted all {deleted_count} records.'})
            
        elif ids and isinstance(ids, list):
            deleted_count, _ = model.objects.filter(id__in=ids).delete()
            return JsonResponse({'status': 'success', 'message': f'Successfully deleted {deleted_count} records.'})
            
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid action or missing IDs'}, status=400)
            
    except LookupError:
        return JsonResponse({'status': 'error', 'message': 'Invalid model name'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
