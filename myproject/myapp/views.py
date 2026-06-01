from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Role, Officer

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
    return render(request, 'users.html')

def villages(request):
    return render(request, 'villages.html')

def sections(request):
    return render(request, 'sections.html')

def varieties(request):
    return render(request, 'varieties.html')

def plots(request):
    return render(request, 'plots.html')

def surveys(request):
    return render(request, 'surveys.html')

def add_farmer(request):
    return render(request, 'add_farmer.html')

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
    return render(request, 'add_section.html')

def add_survey(request):
    return render(request, 'add_survey.html')

def add_user(request):
    return render(request, 'add_user.html')

def add_variety(request):
    return render(request, 'add_variety.html')

def add_village(request):
    return render(request, 'add_village.html')

