from django.conf.urls.defaults import *

urlpatterns = patterns('scaffold.views', 
    url(r'^(?P<section_path>.+)$', 'section', name="section"),
    
)