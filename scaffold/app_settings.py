import re

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.importlib import import_module

_project_settings_registry = []

def _get_setting(project_setting_name, default=None, required=False):
    project_setting_name = "SCAFFOLD_%s" % project_setting_name
    _project_settings_registry.insert(0, project_setting_name)
    if required and not default:
            assert hasattr(settings, project_setting_name), (
                "The following setting is required to use the scaffold "                    
                "application in your project: %s"
            ) %  project_setting_name
    return getattr(settings, project_setting_name, default)

EXTENDING_APP_NAME = _get_setting('EXTENDING_APP_NAME', 
    required=True
)

EXTENDING_MODEL_PATH = _get_setting('EXTENDING_MODEL_PATH',     
    default = "%s.models.Section" % EXTENDING_APP_NAME
)

LINK_HTML = _get_setting('LINK_HTML', default=(
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
))

PATH_CACHE_TTL = _get_setting('PATH_CACHE_TTL',
    default = (60 * 60 * 12)
)
PATH_CACHE_KEY = _get_setting('PATH_CACHE_KEY',
    default="scaffold-path-map" 
)

ALLOW_ASSOCIATED_ORDERING = _get_setting('ALLOW_ASSOCIATED_ORDERING',   
    default=True
)

VALIDATE_GLOBALLY_UNIQUE_SLUGS = _get_setting('VALIDATE_GLOBALLY_UNIQUE_SLUGS',   
    default=False
)

TREEBEARD_NODE_TYPE = _get_setting('TREEBEARD_NODE_TYPE',
    default="treebeard.mp_tree.MP_Node"
)

def get_extending_model():
    """
    This function returns the model that subclasses BaseSection.
    Since it's that real, non-abstract model we usually want to
    deal with, this function will be used extensively in views and
    middlewares. 
    """
    model_path = EXTENDING_MODEL_PATH.split(".")
    model_name = model_path.pop()
    submodule = model_path[-1]
    import_path = ".".join(model_path)
    models = __import__(import_path, fromlist=[submodule])
    return getattr(models, model_name)

def get_treebeard_node_class():
    """
    This function returns the Treebeard node type specified in the 
    ``TREEBEARD_NODE_TYPE`` value in this module or in the 
    ``SCAFFOLD_TREEBEARD_NODE_TYPE`` value in the main project settings
    file. Allowed values are:
        
        'treebeard.mp_tree.MP_Node'
        'treebeard.al_tree.AL_Node'
        'treebeard.ns_tree.NS_Node'
        
    Refer to the treebeard docs for an explanation of each type.
    
    """
    allowed_node_types = (
        'treebeard.mp_tree.MP_Node',
        'treebeard.al_tree.AL_Node',
        'treebeard.ns_tree.NS_Node',
    )
    if TREEBEARD_NODE_TYPE not in allowed_node_types:
        raise ImproperlyConfigured, (
            "The SCAFFOLD_TREEBEARD_NODE_TYPE setting must be one of the " 
            "following: %s."
        ) % ", ".join(allowed_node_types)
    try:
        klass_name = re.search('\.(\w*)$', TREEBEARD_NODE_TYPE).groups()[0]
    except AttributeError:
        raise ImproperlyConfigured, (
            "The SCAFFOLD_TREEBEARD_NODE_TYPE setting could not be parsed"
        )
    module_name = TREEBEARD_NODE_TYPE.replace("." + klass_name, '')
    try:
        module = import_module(module_name)
    except ImportError:
        raise ImproperlyConfigured, (
        "The module %s could not be imported. Please check your "
        "SCAFFOLD_TREEBEARD_NODE_TYPE setting."
        ) % module_name
    if not hasattr(module, klass_name):
        raise ImproperlyConfigured, (
        "The class %s could not be found in the module %s. Please check "
        "your SCAFFOLD_TREEBEARD_NODE_TYPE setting."
        ) % (klass_name, module_name)            
    return getattr(module, klass_name)
