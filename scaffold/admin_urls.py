from django.conf.urls.defaults import *
from django.core.urlresolvers import reverse
from django.views.generic import simple

import app_settings

urlpatterns = patterns('scaffold.admin_views', 
    # We will 'namespace' the index name to avoid collisions with other 
    # admin view names. 
    url(r'^$', 'index', 
        name="sections_index"
    ),
    url(r'^add-to/(?P<section_id>[\w-]+)/?$', 'add_to', 
        name="add"
    ), 
    url(r'^delete/(?P<section_id>\d+)/?$', 'delete', 
        name="delete"
    ), 
    url(r'^edit/(?P<section_id>\d+)/?$', 'edit', 
        name="edit"
    ), 
    url(r'^related/(?P<section_id>\d+)/?$', 'related_content',             
        name="related_content"
    ),     
    url(r'^move/(?P<section_id>\d+)/?$', 'move', 
        name="move"
    ),
    url(r'^order/(?P<section_id>\d+)/?$', 'order_all_content', 
    name="order"
    ),    
)

# This helps correct an issue with the way the admin generates it's URLS. 
# It will try to create /admin/sections/section -- which does not exist.
# This sends it up one level to the main Sections admin page.
urlpatterns = urlpatterns + patterns('django.views.generic.simple',   
    (r'^section/$', 'redirect_to', {'url': '../'})
)