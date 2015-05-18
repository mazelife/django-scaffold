from django.core.exceptions import MiddlewareNotUsed, ImproperlyConfigured
from django.contrib.flatpages.views import flatpage
from django.db.models.loading import AppCache
from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext

from middleware import get_current_section, lookup_section
import app_settings 

Section = app_settings.get_extending_model()

def section(request, section_path=None, id_override=None):
    """
    A view of a section.
    """
    try:
        section = get_current_section()
    except MiddlewareNotUsed:
        lookup_from = id_override or request
        section = lookup_section(lookup_from)
    if section:
        return render_to_response("scaffold/section.html", {'section': section}, context_instance=RequestContext(request))
    else:
        app_cache = AppCache()
        try:
            app_cache.get_app('flatpages')
            try:
                return flatpage(request, request.path_info)
            except Http404:
                pass
        except ImproperlyConfigured:
            pass
        raise Http404, "Section does not exist."