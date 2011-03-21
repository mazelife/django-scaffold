from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.db import models
from django.utils.translation import ugettext_lazy as _

from treebeard.mp_tree import MP_Node

import app_settings

Treebeard_Base_Class = app_settings.get_treebeard_node_class()

class BaseSection(Treebeard_Base_Class):
    """
    An abstract model of a section or subsection. This class provides a base
    level of functionality that should serve as scaffold for a custom section
    object.
    """
    title =  models.CharField(_("Title"), max_length=255)
    slug = models.SlugField(_("Slug"), 
        help_text=_("Used to construct URL"),
        unique = app_settings.VALIDATE_GLOBALLY_UNIQUE_SLUGS
    )
    order = models.IntegerField(_("Order of section"), blank=True, default=0)
    
    class Meta:
        abstract = True
        permissions = (
            ('can_view_associated_content', 'Can view associated content',),
        )
        ordering = ['path']
    
    def __unicode__(self):
        indent_string = "-" * (self.get_depth() - 1)
        return indent_string + self.title
        
    @property
    def full_path(self):
        section_path = [node.slug for node in self.get_ancestors()] 
        section_path.append(self.slug)
        return "/".join(section_path)
    
    @models.permalink
    def get_absolute_url(self):
        return ("section", (), {'section_path': self.full_path})
    
    @property
    def type(self):
        """
        A property that returns the string 'section' if the section is at the 
        root of the tree, 'subsection' otherwise.
        """
        return self.is_root and 'section' or 'subsection'    
    
    def get_first_populated_field(self, field_name):
        """
        Returns the first non-empty instance of the given field in the 
        sections tree. Will crawl from leaf to root, returning `None` if no 
        non-empty field is encountered.
        """
        assert hasattr(self, field_name), "Field name does not exist."
        node = self
        if getattr(node, field_name, None):
            return getattr(node, field_name)
        while not node.is_root():
            node = node.get_parent()
            if getattr(node, field_name, None):
                return getattr(node, field_name)            
        return None
    
    def get_related_content(self, sort_fields=[], infer_sort=False):
        """
        A method to access content associated with a section via a foreign-key 
        relationship of any type. This includes content that's attached via a 
        simple foreign key relationship, and content that's attached via a 
        generic foreign key (for example, through a subclass of the  
        SectionItem model).
        
        This method returns a list of tuples::
        
            (object, app name, model name, relationship_type)
        
        To sort associated content, pass a list of sort fields in via the 
        sort_fields argument. For example, let's say we have two types of 
        content we know could be attached to a section: articles and profiles      
        Articles should be sorted by their 'headline' field, while profiles 
        should be sorted by their 'title' field. We would call our method 
        thusly::
       
            section = Section.objects.all()[0]
            section.get_related_content(sort_fields=['title', 'headline'])
        
        This will create a common sort key on all assciated objects based on    
        the first of these fields that are present on the object, then sort 
        the entire set based on that sort key. (NB: This key is temporary and 
        is removed from the items before they are returned.) 
        
        If 'infer_sort' is True, this will override the sort_fields options 
        and select each content type's sort field based on the first item in 
        the 'ordering' property of it's Meta class. Obviously, infer_sort will  
        only work if the types of fields that are being compared are the same.
        
        """
        associated_content = []
        object_ids = []
        if infer_sort:
            sort_fields = set()
        for rel in self._meta.get_all_related_objects():
            try: 
                fk_items = getattr(self, rel.get_accessor_name())
            except self.DoesNotExist:
                continue
            else:
                for fk_item in fk_items.all():
                    # If this is a generic relation, fetch content object.
                    if hasattr(fk_item, 'content_object'):
                        fk_item = fk_item.content_object    
                        relationship_type = 'generic-foreign-key'
                    else:
                        relationship_type = 'foreign-key'
                    # In the weird edge-case where an item is related to a 
                    # section in more than one way, we only want the item to 
                    # appear in this list once. Therefore, we ID items by app, 
                    # model and pk and verify we haven't already seen that ID 
                    # before adding the item to our list.
                    object_id = "%s/%s/%s" % (
                        fk_item._meta.app_label,
                        fk_item._meta.object_name,
                        str(fk_item.pk)
                    )
                    if object_id not in object_ids:
                        object_ids.insert(0, object_id)
                        associated_content.insert(0,(
                            fk_item, 
                            fk_item._meta.app_label,
                            fk_item._meta.object_name,
                            relationship_type                    
                        ))
                        if infer_sort and len(fk_item._meta.ordering) > 0:
                            sort_fields.add(fk_item._meta.ordering[0])
        if not len(sort_fields) == 0:
            for item, app, model, rel in associated_content:
                for sort_field in sort_fields:
                    if hasattr(item, sort_field):
                        key = getattr(item, sort_field)
                        setattr(item, '_associated_content_tmp_sort_key', key)
                        break
            
            def sort_content(x, y):
                return cmp(
                    getattr(x[0], '_associated_content_tmp_sort_key', None),
                    getattr(y[0], '_associated_content_tmp_sort_key', None)
                )
            
            associated_content.sort(sort_content)
            for item in associated_content:
                if hasattr(item, '_associated_content_tmp_sort_key'):
                    delattr(item, '_associated_content_tmp_sort_key')
        return associated_content

    def get_subsections(self):
        """
        This method return all subsections of the current section.
        """
        return self.get_children().select_related()
        
    def get_associated_content(self, only=[], sort_key=None):
        """
        This method returns an aggregation of all content that's associated 
        with a section, including subsections, and other objects related via 
        any type of foreign key. To restrict the types of objetcs that are
        returned from foreign-key relationships, the only argument takes a  
        list of items with the signature::  
            
            {app name}.{model name}
            
        For example, if you wanted to retrieve a list of all subsections and 
        associated articles only, you could do the following::
            
            section = Section.objects.all()[0]
            section.get_associated_content(only=['articles.article'])
            
        Furthermore, if all objects have a commone sort key, you can specify 
        that with the sort_key parameter. So, since sections have an 'order' 
        field, if articles had that field as well, you could do the following::
            
            section = Section.objects.all()[0]
            section.get_associated_content(
                only=['articles.article'], 
                sort_key='order'
            )
            
        ...and the list returned would be sorted by the 'order' field.
        """
        
        related_content = self.get_related_content()
        associated_content = []
        if len(only) != 0:
            for obj, app, model, rel in related_content:
                if "%s.%s" % (app, model) in only:
                        setattr(obj, 'content_type', "%s.%s" % (app, model))
                        associated_content.insert(0, (
                            obj,
                            app,
                            model,
                            rel
                        ))
        else:
            for obj, app, model, rel in related_content:
                setattr(obj, 'content_type', "%s.%s" % (app, model))
                associated_content.insert(0, (
                    obj,
                    app,
                    model,
                    rel
                ))
        for subsection in self.get_subsections():
            app = subsection._meta.app_label
            model = subsection._meta.object_name
            if len(only) == 0 or app + "." + model in only: 
                associated_content.insert(0, (
                    subsection,
                    app,
                    model,
                    'subsection'
                ))

        def sort_list(x, y):
            if not hasattr(x[0], sort_key):
                if not hasattr(y[0], sort_key):
                    return x
                else:
                    return y
            return cmp(getattr(x[0],sort_key),getattr(y[0],sort_key))

        if sort_key:
            associated_content.sort(cmp=sort_list)
        return associated_content

class SectionItem(models.Model):
    """A model of a generic relation between any item and a section"""
    section = models.ForeignKey('Section')
    content_type = models.ForeignKey(ContentType)    
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()
    
    class Meta:
        abstract = True
            
    def __unicode__(self):
        fk_app = self.content_object._meta.app_label
        fk_model = self.content_object.__class__.__name__
        fk_str = self.content_object.__unicode__()        
        return u"%s.%s: %s" % (fk_app, fk_model, fk_str)