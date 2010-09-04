from django.conf import settings

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

def get_extending_model():
    """
    This method returns the model that subclasses BaseSection.
    Since it's that real, non-abstract model we usually want to
    deal with, this funcion will be used extensively in views and
    midllewares. 
    """
    model_path = EXTENDING_MODEL_PATH.split(".")
    model_name = model_path.pop()
    submodule = model_path[-1]
    import_path = ".".join(model_path)
    models = __import__(import_path, fromlist=[submodule])
    return getattr(models, model_name)
