=====================================
Creating an app to extend scaffold
=====================================

Although you've installed it, scaffold won't do much by itself. Think of it as a kind of *abstract* application, akin to the notion of an abstract class in python. In other words, scaffold is meant to be extended by an application that you create. We'll call this the **concrete app** from here on out.

This is not to say scaffold doesn't have a lot going on under the hood; like any Django app, scaffold has views, models, templates and media files. However, any one of these elements can--and should be--extended or overridden as needed. Let's walk through the steps we'll need to get a basic **concrete app** working using scaffold.

A typical use case for scaffolding is creating a tree of sections and subsections for a web site. Let's say we're putting together a simple news site, which will have sections for news, weather, entertainment and shopping. Some of these sections--entertainment--will have sub-sections (say, movies, theater, music, and art). Content creators will be able to create articles which can be attached to any one of these sections and subsections. All in all, a simple, common task for a web developer and one that scaffold can help with.

1. Create a new application. 
------------------------------
Let's start by creating an application for handling sections in the site. We'll even call the application "sections":

.. code-block:: bash

    python manage.py startapp sections

2. Create a model which extends scaffold
-----------------------------------------

We decide that a section should have a title, a description (which we'll use in meta tags for SEO purposes), and a photo. We'll start by creating a model in the models.py file that extends the ``scaffold.models.BaseSection`` model.
Here's some of what's in that ``BaseSection`` model::

    class BaseSection(MP_Node):

        slug = models.SlugField(_("Slug"), help_text=_("Used to construct URL"))
        title =  models.CharField(_("Title"), max_length=255)
        order = models.IntegerField(_("Order of section"), blank=True, default=0)

Notice that the model only defines 3 fields. Let's ignore "order" for the moment; scaffold assumes that anything that extends ``BaseSection`` will have at least a slug (for constructing the url of the section) and a title.

Now we can create a model which adds the fields we need. In the ``models.py`` for your new app, add the following::

    from scaffold.models import BaseSection
    
    class Section(BaseSection):
        description = models.TextField("Description", help_text="For SEO.")
        photo = models.ImageField("Photo", upload_to="section_images")

...and that's it, we're done. BaseSection provides a number of powerful methods that we'll get into later.

3. Setup your URL Configuration
---------------------------------

Change the default urls.py file for your Django project to the following::

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


We've done a couple things here. First, we've enabled the admin app by uncommenting the lines which turn on autodiscover and route ``/admin/`` urls to the admin app. Then we've inserted a line **above** the ``^admin/`` url configuration which route urls sepcific to our new app to a different url conf that is used for the scaffold admin views.

That takes care of the admin interface and allows us to manage a sections/subsections tree in the admin. But how will we actually view a section or subsection on the website? The final url pattern handles this::

        url(r'^(?P<section_path>.+)/$', 'scaffold.views.section', name="section")
        
This line works for a very specific, but common URL addressing schema: Top level sections will have root-level slugs in the url. Our site has an "Entertainment" section with the slug ``entertainment``. The URL will therefore be **http://www.mysite.com/entertainment/**. There is also a subsection of entertainment, called "Dining Out" with the slug ``dining``. It's URL would be **http://www.mysite.com/entertainment/dining/**. 

Like almost everything about scaffold, you are not required to use this pattern. You can write your own url conf, or completely override the ``scaffold.views.section`` view if you like. 
        
.. admonition:: Note

    The positioning of the url patterns here is very deliberate. The regular         expression '^(?P<section_path>.+)/$' is rather  greedy and will match anything, therefore we put it last. Conversely, the regular expression '^admin/sections/section/' is more specific than the '^admin/' expression, so we place it first to ensure that it overrides the standard admin pages for our app.

4. Register your Section model in the admin site
----------------------------------------------------

Create an admin.py file in your concrete application and register your new ``Section`` model there::

    from django.contrib import admin
    from models import Section
    from scaffold.admin import SectionAdmin

    admin.site.register(Section, SectionAdmin)


5. Add the necessary project settings
-----------------------------------------

All that's left to do is add a single setting to your Django project. 
In your settings.py file, place the following::

    SCAFFOLD_EXTENDING_APP_NAME = 'sections'
    
    
Note: this example assumes your concrete app is called `sections`. Use whatever you've named your app as the `SCAFFOLD_EXTENDING_APP_NAME` setting.

6. Make the the scaffold media available. 
------------------------------------------

Django-scaffold has a number of CSS, JavaScript and image files which it uses in the admin interface. These are stored in media/scaffold in the scaffold application directory. You can copy scaffold from it's media directory to your own project's media directory, but it's best to simply create a symlink instead. (Make sure, if you're using apache to server this, you have the ``Options FollowSymLinks`` directive in place.)

At this point, you should be able to start up your Django project, browse to the admin interface and start creating sections.