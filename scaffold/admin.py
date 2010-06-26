from django.contrib import admin
from django.contrib.contenttypes import generic
from django.db import models

from forms import SectionForm
import app_settings
Section = app_settings.get_extending_model()


class SectionAdmin(admin.ModelAdmin):
    
    class Media:
        css = {
            "all": ("scaffold/styles/scaffold-admin.css",)
        }
        
    form = SectionForm
    list_per_page = 10
    
    def __init__(self, *args, **kwargs):
        from admin_urls import urlpatterns       
        for regex_URL_pattern in urlpatterns:
            if regex_URL_pattern.name == 'related_content':
                regex_URL_pattern.default_args = {
                    'list_per_page': self.list_per_page
                }
        self.urlpatterns = urlpatterns
        self.url_map = dict([(p.name, p.callback) for p in urlpatterns])
        super(SectionAdmin, self).__init__(*args, **kwargs)
    
    def get_urls(self):
        urls = super(SectionAdmin, self).get_urls()
        return self.urlpatterns
    
    def changelist_view(self, request):
        index_view = self.url_map['sections_index']
        return index_view(request)
    
    def add_view(self, request):
        from django.views.generic import simple
        return simple.redirect_to(request, '../../')