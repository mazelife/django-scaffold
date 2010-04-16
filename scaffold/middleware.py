from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import MiddlewareNotUsed
from django.db.models.signals import post_save, post_delete

import settings as app_settings
Section = app_settings.get_extending_model()

# Import and work-around for python < 2.4
try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local
_thread_locals = local()

def _build_section_path_map():
    """
    Simple wrapper around Django's low level cache; stores and populates 
    a list of all section urls using the low-level caching framework.
    """
    paths = {}
    for section in Section.objects.all():
        paths[section.get_absolute_url()] = section.slug
    cache.set(app_settings.PATH_CACHE_KEY, paths, app_settings.PATH_CACHE_TTL) 
    return paths

def _get_section_path_map():
    """
    Simple wrapper around Django's low level cache; retrieves (and, if 
    necessary, first populates) a list of all section urls using.
    """
    paths = cache.get(app_settings.PATH_CACHE_KEY)
    if not paths:
        return _build_section_path_map()
    return paths

def get_current_section():
    """
    Convenience function to get the current section from the thread of the
    currently executing request, assuming there is one. If not, returns None.
    NB: Make sure that the SectionsMiddleware is enabled before calling this
    function. If it is not enabled, this function will raise a
    MiddlewareNotUsed exception. 
   
    """
    if not getattr(_thread_locals, 'sections_middleware_enabled', None):
        raise MiddlewareNotUsed, (
            'SectionsMiddleware is not used in this server configuration. '
            'Please enable the SectionsMiddleware.'
        )
    return getattr(_thread_locals, 'section', None)

def lookup_section_from_request(request):
    section = None
    path_map = _get_section_path_map()
    path = request.path
    paths = path_map.keys()
    paths.sort(lambda x, y: len(x) <= len(y) and 1 or -1)
    matches = [p for p in paths if path.startswith(p)]
    if len(matches) >= 1:
        section = Section.objects.get(slug=path_map[matches[0]])
    return section        

class SectionsMiddleware(object):
    """
    Middleware that stores the current section (if any) in the thread of the 
    currently executing request
    """
    
    def process_request(self, request):
        section = lookup_section_from_request(request)
        _thread_locals.section = section
        _thread_locals.sections_middleware_enabled = True

def reset_section_path_map(sender, **kwargs):
    _build_section_path_map()

# Rebuild path map when a section is saved or removed.
# See http://code.djangoproject.com/wiki/[...]
# Signals#Helppost_saveseemstobeemittedtwiceforeachsave
# for an explanation of why dispatch_uid is needed.
post_save.connect(reset_section_path_map, 
    sender=Section, 
    dispatch_uid="paths-reset"
)
post_delete.connect(reset_section_path_map, 
    sender=Section, 
    dispatch_uid="paths-reset"
)