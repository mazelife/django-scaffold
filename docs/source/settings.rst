===========================================
Available settings
===========================================

Here's a full list of all available settings for the django-scaffold application, in alphabetical order, and their
default values.

SCAFFOLD_ALLOW_ASSOCIATED_ORDERING
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``True``

One of scaffold's features is that you can order multiple types of content that is attached to a scaffold item. For example, lets say you extend ``scaffold.models.BaseSection`` with a model called Section. By it's very nature, one section can be the child of another. However, you might also create a model called ``Article`` which has a Foreign-key relationship with a section, and thus is it's child too. In fact you might even establish a generic foreign key relationship between a model and your ``Section`` model. When this property is set to True, you can order all items relative to each other via the admin interface.

Note that for this to work, all models must share a common field were the order, relative to each other, can be stored as an integer. By default, models that inherit from ``scaffold.models.BaseSection``assume this field is called 'order'. 

If you don't want this ordering option to be available in the admin interface for associated content, set this to False.

SCAFFOLD_EXTENDING_APP_NAME
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: Not defined

The name of the concrete application which is extending scaffold. Note that this setting is required: scaffold will not work without it.

SCAFFOLD_EXTENDING_MODEL_PATH
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``'{SCAFFOLD_EXTENDING_APP_NAME}.models.Section'``

The location of the model which extends ``scaffold.models.BaseSection``. By default, it assumes this model is called ``Section``, thus if you create an app named "pages", scaffold will try to import ``pages.models.Section`` unless this setting is provided.

SCAFFOLD_LINK_HTML
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default::
    
    (
        ('edit_link', (
            "<a class=\"changelink\" href=\"%s/\">"
            "edit</a>"
        ),),
        ('add_link', (
            "<a class=\"addlink\" href=\"%s/create/\">"
            "add child</a>"
        ),),
        ('del_link', (
            "<a class=\"deletelink\" href=\"%s/delete/\">"
            "delete</a>" 
        ),),
        ('list_link', (
            "<a class=\"listlink\" href=\"%s/related/\">"
            "list content</a>" 
        ),)
    )

These are the four links which are added to every item in the tree in the scaffold admin view. You can override this tuple of tuples with your own links, or reorder this one.

SCAFFOLD_PATH_CACHE_KEY
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``'scaffold-path-map'``

The key name under which scaffold stores it's path cache values. This should only be changed to avoid key collisions in the cache

SCAFFOLD_PATH_CACHE_TTL
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``43200`` (that's equal to 12 hours)

The length of time (in seconds) an item persists in the path cache. The path cache is a way of very quickly (and without a DB call) looking up scaffold items from a url. Note that that adding, editing the slug of, or removing a scaffold item automatically refreshes the cache.