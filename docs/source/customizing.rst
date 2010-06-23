=============================
Customizing scaffold
=============================

In the previous section (:doc:`extending`) we created an app that used scaffold, but the only thing we customized was the model the app used. We used the URL conf, views, and templates provided by scaffold, but we don't have to.

Almost any piece of scaffold can be overridden in your concrete app. For example, let's say we want to create our own view of our ``Section`` model, rather than using scaffold's. And while we're at it, we want to change how the url addressing of sections works.

Customizing URLs
-----------------

By default, scaffold uses a common URL addressing scheme for sections and subsections. A url like ``"/projects/local/water/"`` means give me the section with the slug "water", which is a child of the "local" section, which in turn is a child of the "projects" section. This is a common--and useful way--of orienting the user within the IA of the site using the URL.

But, let's say you want a simpler scheme, with URLs like ``"/sections/local/"`` or ``"/sections/water/"``. Heres how our URL conf file looked at the end of the last section::

    from django.conf.urls.defaults import *

    from django.contrib import admin
    admin.autodiscover()
    urlpatterns = patterns('',
        (r'^admin/sections/section/', include('scaffold.admin_urls', 
            namespace="scaffold"
        )),
        (r'^admin/', include(admin.site.urls)),
        url(r'^(?P<section_path>.+)/$', 'scaffold.views.section', name="section"),
    )

Now we can make the urlpatterns look like this::

    urlpatterns = patterns('',
        url(r'^sections/(?P<slug>[\w-]+)/?$', 'scaffold.views.section', name="section"),
        (r'^admin/sections/section/', include('scaffold.admin_urls', 
            namespace="scaffold"
        )),
        (r'^admin/', include(admin.site.urls)),
    )

Customizing Views
------------------

The one problem is that we aren't passing scaffold.views.section the arguments it wants anymore, so we'll need to create our own view function::

    urlpatterns = patterns('',
        url(r'^sections/(?P<slug>[\w-]+)/?$', 'sections.views.section'),
        (r'^admin/sections/section/', include('scaffold.admin_urls', 
            namespace="scaffold"
        )),
        (r'^admin/', include(admin.site.urls)),
    )

Then we create a "section" view in our app's *views.py* file::

    from django.shortcuts import get_object_or_404  
    from django.views.generic import simple
    from models import Section

    def section(request, slug=None):
        section = get_object_or_404(Section, slug=slug)
        return simple.direct_to_template(request,
            template="scaffold/section.html",
            extra_context={
                'section': section,
            }
        )

Customizing Templates
----------------------

We're still using scaffold's template, but this is probably one of the first thing's you'd want to override. You can do this in two ways: create a ``scaffold`` directory in your own project's templates folder, then create a ``section.html`` file where you template the object yourself. Or, if you've written your own view function like we have, then you can call the template whatever you want::

    from django.shortcuts import get_object_or_404  
    from django.views.generic import simple
    from models import Section

    def section(request, slug=None):
        section = get_object_or_404(Section, slug=slug)
        return simple.direct_to_template(request,
            template="sections/section.html",
            extra_context={
                'section': section,
            }
        )

Customizing the Admin
-------------------------

One of scaffold's best features is it's integration with the Django admin. Even this, however, is customizable. One of the reasons scaffold has a ``views`` module *and* a ``admin_views`` module is that it's highly likely you'll need to customize your application's public views, but not the admin ones. But if you do want to override the admin views, go for it. (Just keep in mind the admin_views module is just under 500 lines of code.)::

  urlpatterns = patterns('',
      url(r'^sections/(?P<slug>[\w-]+)/?$', 'sections.views.section'),
      (r'^admin/sections/section/', include('sections.admin_urls', 
          namespace="scaffold"
      )),
      (r'^admin/', include(admin.site.urls)),
  )


