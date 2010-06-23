==============================================
Customizing the admin interface
==============================================

Some admin customizations are possible in Django scaffold, although not as many as in a standard ``ModelAdmin`` class because of differences in the UI.

``SectionAdmin`` media definitions
------------------------------------

There are times where you would like add a bit of CSS and/or JavaScript to
the add/change views. This can be accomplished by using a Media inner class
on your ``SectionAdmin``, same as you would for a class inheriting from ``ModelAdmin``::

    class ArticleAdmin(admin.SectionAdmin):
        class Media:
            css = {
                "all": ("my_styles.css",)
            }
            js = ("my_code.js",)


For full detail on how to use this feature, see the `Django documentation <http://docs,djangoproject.com/en/dev/ref/contrib/admin/#modeladmin-media-definitions>`_ on it.

``SectionAdmin`` field exclusion
-------------------------------------

This attribute, if given, should be a list of field names to exclude from the
form.

For example, let's consider the following model::

    class Author(models.Model):
        name = models.CharField(max_length=100)
        title = models.CharField(max_length=3)
        birth_date = models.DateField(blank=True, null=True)

If you want a form for the ``Author`` model that includes only the ``name``
and ``title`` fields, you would specify ``fields`` or ``exclude`` like this::

    class AuthorAdmin(admin.SectionAdmin):
        fields = ('name', 'title')

    class AuthorAdmin(admin.SectionAdmin):
        exclude = ('birth_date',)

For full detail on how to use this attribute, see the `Django documentation <http://docs,djangoproject.com/en/dev/ref/contrib/admin/#modeladmin-options>`_ on it.

``SectionAdmin`` Fieldsets
-----------------------------

Set ``fieldsets`` to control the layout of admin "add" and "edit" pages.

``fieldsets`` is a list of two-tuples, in which each two-tuple represents a
``<fieldset>`` on the admin form page. (A ``<fieldset>`` is a "section" of the
form.)

The two-tuples are in the format ``(name, field_options)``, where ``name`` is a
string representing the title of the fieldset and ``field_options`` is a
dictionary of information about the fieldset, including a list of fields to be
displayed in it.

An example::

    class SectionAdmin(admin.SectionAdmin):
    
        fieldsets = (
            (None, {
                'fields': ('slug', 'title',)
            }),
            ('Advanced options', {
                'fields': ('description',)
            }),
        )

For full detail on how to use this attribute, see the `Django documentation <http://docs,djangoproject.com/en/dev/ref/contrib/admin/#modeladmin-options>`_ on it.