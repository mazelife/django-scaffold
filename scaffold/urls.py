from django.conf.urls.defaults import *

import settings as app_settings

urlpatterns = patterns(app_settings.EXTENDING_VIEW_PATH, 
    url(r'^(?P<section_path>.+)$', 'section', name="section"),
    
)