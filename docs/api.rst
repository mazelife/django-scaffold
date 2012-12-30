============================
The scaffold API
============================

Model methods
-------------

The following methods are provided by ``scaffold.models.BaseSection``:

.. autoclass:: scaffold.models.BaseSection
    :members: type,get_first_populated_field,get_related_content,get_subsections,get_associated_content

Admin
-------

The sections application contains the following views.

.. autoclass:: scaffold.admin.SectionAdmin
    :members:

Middleware
-----------

Use the middleware if you need access to the section outside the view context.

.. automodule:: scaffold.middleware
    :members:
    :undoc-members:
