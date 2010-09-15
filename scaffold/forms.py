from django import forms

import app_settings

class SectionForm(forms.ModelForm):
    """
    Form for working with ``BaseSection``-inheriting models.
    Saving new items is disabled.
    """
        
    class Meta:
        model = app_settings.get_extending_model()
        exclude = ('path', 'depth', 'numchild', 'order')
    
    def save(self, *args, **kwargs):
        """
        We're overriding this because we don't want to use Django's ORM to
        create new nodes. Django-treebeard has it's own node creation methods
        which should be used instead. To make sure no one actually uses this
        ``ModelForm`` to do that, calling it's save method will raise a 
        ``NotImplemented`` exception, **unless an instance has been supplied**. 
        In that case, we're just updating an existing node, so using the ORM to 
        save is fine.
        """
        if hasattr(self, 'instance') and self.instance:
            return super(SectionForm, self).save(*args, **kwargs)
        raise NotImplementedError, (
            "Use django-treebeard's native methods to create new nodes."
        )