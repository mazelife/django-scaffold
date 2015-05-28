try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('scaffold.views', 
    url(r'^(?P<section_path>.+)$', 'section', name="section"),
    
)