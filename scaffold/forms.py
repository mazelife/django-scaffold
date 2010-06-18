from django import forms
from django.contrib.admin import widgets as admin_widgets
from django.contrib.contenttypes.generic import generic_inlineformset_factory
from django.utils.translation import ugettext_lazy as _

import app_settings

class SectionForm(forms.ModelForm):
    """Form for working with Sections. Saving new sections is disabled."""
        
    class Meta:
        model = app_settings.get_extending_model()
        exclude = ('path', 'depth', 'numchild', 'order')
    
    def save(self, *args, **kwargs):
        """
        We're overriding this beacuse we don't want to use Django's ORM to
        create new nodes. django-treebeard has it's own node creation methods
        which should be used instead. To make sure no one actually uses this
        ModelForm to do that, calling it's save method will raise a 
        NotImplemented exception, **unless an instance has been supplied**. In
        that case, we're just updating an existing node, so using the ORM to 
        save is fine.
        """
        if hasattr(self, 'instance') and self.instance:
            return super(SectionForm, self).save()
        raise NotImplementedError, (
            "Use django-treebeard's native methods to create new nodes."
        )