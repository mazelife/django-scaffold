from django.conf.urls.defaults import *

import app_settings

urlpatterns = patterns('scaffold.views', 
    url(r'^(?P<section_path>.+)$', 'section', name="section"),
    
)