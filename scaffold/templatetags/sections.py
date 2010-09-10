from django import template

from scaffold import app_settings
Section = app_settings.get_extending_model()

register = template.Library()

class SectionNode(template.Node):

    def __init__(self, section=None, as_varname=None):
        self.as_varname = as_varname
        self.current_section = section

    def _resolve_section(self, context):
        """
        Return the section variable passed into the constructor, if 
        the variable can be resolved within the template context.
        """
        if self.current_section:
            current_section = template.Variable(self.current_section)
            try:
                current_section = current_section.resolve(context)
            except template.VariableDoesNotExist:
                current_section = None
        else:
            current_section = None
        return current_section

    def render(self, context):
        root_sections = Section.get_root_nodes()
        current_section = self._resolve_section(context)     
        if current_section:
            for section in root_sections:
                is_active = current_section.is_descendant_of(section) \
                    or current_section.pk == section.pk
                setattr(section, 'is_active', is_active)
        context[self.as_varname] = root_sections
        return ''

@register.tag
def get_root_sections(parser, token):
    """
    Gets the list of comments for the given params and populates the template
    context with a variable containing that value, whose name is defined by the
    'as' clause.

    Syntax::

        {% get_root_sections with [section] as [varname]  %}
        {% get_root_sections as [varname]%}

    Example usage::

        {% get_root_sections with subsection as root_sections %}
        {% for section in root_sections %}
            ...
        {% endfor %}

    """
    tokens = token.split_contents()
    if tokens[1] not in ['with', 'as']:
        raise template.TemplateSyntaxError(
            "Second argument in %r tag must be 'with' or 'as'." % tokens[0]
        )
    if tokens[1] == 'as': # get_root_sections as [varname]
        varname = tokens[2]
        section = None
    else: # get_root_sections with [section slug] as [varname]
        if tokens[3] != 'as':
            raise template.TemplateSyntaxError(
                "Fourth argument in %r tag must be 'as'." % tokens[0]
            )
        section = tokens[2]
        varname = tokens[4]
    return SectionNode(section=section, as_varname=varname)

class SectionDescendantNode(template.Node):
    
    def __init__(self, section_var, ancestor_var, varname):
        self.section_var = template.Variable(section_var)
        self.ancestor_var = template.Variable(ancestor_var)
        self.varname = varname
    
    def _resolve_vars(self, context):
        try:
            section = self.section_var.resolve(context)
            ancestor = self.ancestor_var.resolve(context)
        except template.VariableDoesNotExist:
            return (None, None,)
        return (section, ancestor,)

    def render(self, context):
        section, ancestor = self._resolve_vars(context)
        if not section or not ancestor:
            context[self.varname] = None
            return ''
        result = section.is_descendant_of(ancestor) or \
            section.pk == ancestor.pk
        context[self.varname] = result
        return ''
    
@register.tag
def section_is_descendant(parser, token):
    """
    Syntax::

        {% section_is_descendant [section] of [ancestor] as [varname]  %}

    Example usage::

        {% section_is_descendant mysubsection of rootsection as descends %}
        
    """
    tokens = token.split_contents()
    if tokens[2] != 'of' or tokens[4] != 'as' or len(tokens) != 6:
        raise template.TemplateSyntaxError((
            "Incorrect syntax for %r. Format is: {%% section_is_descendant "
            "[section] of [ancestor] as [varname]  %%}"
        ) % tokens[0])          
    section_var = tokens[1]
    ancestor_var = tokens[3]
    varname = tokens[5]
    return SectionDescendantNode(section_var, ancestor_var, varname)

@register.inclusion_tag('scaffold/admin/submit_line.html', takes_context=True)
def submit_row(context):
    """
    Displays the row of buttons for delete and save. 
    """
    opts = context['opts']
    change = context['change']
    is_popup = context['is_popup']
    save_as = context['save_as']
    allow_associated_ordering = context['allow_associated_ordering']
    model_label = context['model_label']
    return {
        'model_label': model_label,
        'allow_associated_ordering': allow_associated_ordering,
        'show_move': not is_popup and change,
        'onclick_attrib': (opts.get_ordered_objects() and change
                            and 'onclick="submitOrderForm();"' or ''),
        'show_delete_link': (not is_popup and context['has_delete_permission']
                              and (change or context['show_delete'])),
        'show_save_as_new': not is_popup and change and save_as,
        'show_save_and_add_another': context['has_add_permission'] and 
                            not is_popup and (not save_as or context['add']),
        'show_save_and_continue': not is_popup and\
            context['has_change_permission'],
        'is_popup': is_popup,
        'show_save': True
    }
    