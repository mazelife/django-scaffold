from django import template

from scaffold import settings as app_settings
Section = app_settings.get_extending_model()

register = template.Library()

class SectionNode(template.Node):

    def __init__(self, section=None, as_varname=None):
        self.as_varname = as_varname
        try:
            self.current_section = section
        except Section.DoesNotExist:
            self.current_section = None

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
        slug = None
    else: # get_root_sections with [section slug] as [varname]
        if tokens[3] != 'as':
            raise template.TemplateSyntaxError(
                "Fourth argument in %r tag must be 'as'." % tokens[0]
            )
        section = tokens[2]
        varname = tokens[4]
    return SectionNode(section=section, as_varname=varname)