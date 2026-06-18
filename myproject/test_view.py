import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from myapp.views import field_intelligence
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware

factory = RequestFactory()
request = factory.get('/')
middleware = SessionMiddleware(lambda r: None)
middleware.process_request(request)
request.session['role_id'] = '2'
request.session['factory_ids'] = '1'
request.session.save()

try:
    response = field_intelligence(request)
    content = response.content.decode('utf-8')
    start = content.find('var rawPlotsData')
    if start != -1:
        print(content[start:start+100])
    else:
        print('Not found')
except Exception as e:
    print('ERROR:', e)
