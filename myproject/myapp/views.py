from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Role, Officer, Section, Village, Farmer, Variety

def index(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        password = request.POST.get('password')
        
        user = Officer.objects.filter(user_id=user_id, password=password).first()
        if user:
            # Login successful, redirect to dashboard
            request.session['user_id'] = user.user_id
            request.session['officer_name'] = user.name
            request.session['permissions'] = user.permissions or []
            request.session['role_id'] = user.role_id
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid User ID or password.')
            return redirect('index')

    return render(request, 'index.html')

def logout_view(request):
    request.session.flush()
    return redirect('index')

def dashboard(request):
    return render(request, 'dashboard.html')

def officers(request):
    officers_list = Officer.objects.all()
    return render(request, 'officers.html', {'officers': officers_list})

def field_intelligence(request):
    return render(request, 'field_intelligence.html')

def analytics(request):
    return render(request, 'analytics.html')

def ndvi_monitoring(request):
    return render(request, 'ndvi_monitoring.html')

def scouting(request):
    return render(request, 'scouting.html')

def reports(request):
    return render(request, 'reports.html')

def settings(request):
    return render(request, 'settings.html')

def users(request):
    farmers_list = Farmer.objects.all()
    return render(request, 'users.html', {'farmers': farmers_list})

def villages(request):
    villages_list = Village.objects.all()
    return render(request, 'villages.html', {'villages': villages_list})

def sections(request):
    sections_list = Section.objects.all()
    return render(request, 'sections.html', {'sections': sections_list})

def varieties(request):
    varieties_list = Variety.objects.all()
    return render(request, 'varieties.html', {'varieties': varieties_list})

def plots(request):
    return render(request, 'plots.html')

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
        
        section = Section.objects.get(id=section_id) if section_id else None
        village = Village.objects.get(id=village_id) if village_id else None
        
        Farmer.objects.create(
            name=name,
            father_name=father_name,
            phone=phone,
            division=division,
            section=section,
            village=village
        )
        return redirect('users')

    sections_list = Section.objects.all()
    villages_list = Village.objects.all()
    return render(request, 'add_farmer.html', {
        'sections': sections_list,
        'villages': villages_list
    })

def add_officer(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        mobile = request.POST.get('mobile')
        email = request.POST.get('email')
        password = request.POST.get('password', 'default123') # We don't have password field in UI yet, but model requires it
        role_id = request.POST.get('role')
        permissions = request.POST.getlist('permissions[]')
        
        role = Role.objects.filter(id=role_id).first() if role_id else None
        
        Officer.objects.create(
            name=name,
            mobile=mobile,
            email=email,
            password=password,
            role=role,
            permissions=permissions
        )
        return redirect('officers')

    roles = Role.objects.all()
    return render(request, 'add_officer.html', {'roles': roles})

def add_plots(request):
    return render(request, 'add_plots.html')

def add_section(request):
    if request.method == 'POST':
        section_name = request.POST.get('section_name')
        description = request.POST.get('description')
        
        Section.objects.create(
            section_name=section_name,
            description=description
        )
        return redirect('sections')

    return render(request, 'add_section.html')

def add_survey(request):
    return render(request, 'add_survey.html')

def add_user(request):
    return render(request, 'add_user.html')

def add_variety(request):
    if request.method == 'POST':
        crop_type = request.POST.get('crop_type')
        variety_name = request.POST.get('variety_name')
        season_id = request.POST.get('season')
        
        season = Section.objects.get(id=season_id) if season_id else None
        
        Variety.objects.create(
            crop_type=crop_type,
            variety_name=variety_name,
            season=season
        )
        return redirect('varieties')
    
    sections_list = Section.objects.all()
    return render(request, 'add_variety.html', {'sections': sections_list})

def add_village(request):
    if request.method == 'POST':
        village_name = request.POST.get('village_name')
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
                section=section,
                taluk=taluk,
                district=district,
                state=state,
                status=status,
                description=description
            )
            return redirect('villages')

    sections_list = Section.objects.all()
    return render(request, 'add_village.html', {'sections': sections_list})

def edit_officer(request, id):
    from django.shortcuts import get_object_or_404
    officer = get_object_or_404(Officer, id=id)
    if request.method == 'POST':
        officer.name = request.POST.get('name')
        officer.mobile = request.POST.get('mobile')
        officer.email = request.POST.get('email')
        role_id = request.POST.get('role')
        officer.role = Role.objects.filter(id=role_id).first() if role_id else None
        officer.permissions = request.POST.getlist('permissions[]')
        password = request.POST.get('password')
        if password:
            officer.password = password
        officer.save()
        return redirect('officers')
    
    roles = Role.objects.all()
    return render(request, 'edit_officer.html', {'officer': officer, 'roles': roles})

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
        
        farmer.section = Section.objects.get(id=section_id) if section_id else None
        farmer.village = Village.objects.get(id=village_id) if village_id else None
        farmer.save()
        return redirect('users')

    sections_list = Section.objects.all()
    villages_list = Village.objects.all()
    return render(request, 'edit_farmer.html', {
        'farmer': farmer,
        'sections': sections_list,
        'villages': villages_list
    })

def edit_village(request, id):
    from django.shortcuts import get_object_or_404
    village = get_object_or_404(Village, id=id)
    if request.method == 'POST':
        village.village_name = request.POST.get('village_name')
        section_id = request.POST.get('section_id')
        village.section = Section.objects.get(id=section_id) if section_id else None
        village.taluk = request.POST.get('taluk')
        village.district = request.POST.get('district')
        village.state = request.POST.get('state')
        village.status = request.POST.get('status')
        village.description = request.POST.get('description')
        village.save()
        return redirect('villages')

    sections_list = Section.objects.all()
    return render(request, 'edit_village.html', {'village': village, 'sections': sections_list})

def edit_section(request, id):
    from django.shortcuts import get_object_or_404
    section = get_object_or_404(Section, id=id)
    if request.method == 'POST':
        section.section_name = request.POST.get('section_name')
        section.description = request.POST.get('description')
        section.save()
        return redirect('sections')

    return render(request, 'edit_section.html', {'section': section})

def edit_variety(request, id):
    from django.shortcuts import get_object_or_404
    variety = get_object_or_404(Variety, id=id)
    if request.method == 'POST':
        variety.crop_type = request.POST.get('crop_type')
        variety.variety_name = request.POST.get('variety_name')
        season_id = request.POST.get('season')
        variety.season = Section.objects.get(id=season_id) if season_id else None
        variety.save()
        return redirect('varieties')
    
    sections_list = Section.objects.all()
    return render(request, 'edit_variety.html', {'variety': variety, 'sections': sections_list})
