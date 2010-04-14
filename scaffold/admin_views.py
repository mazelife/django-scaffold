import operator
from functools import partial

from django.contrib.auth.decorators import permission_required
from django.contrib.admin import site
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseBadRequest, HttpResponseServerError
from django.shortcuts import get_object_or_404
from django.views.generic import simple
from django.http import Http404

import settings as app_settings

app_name =  app_settings.EXTENDING_APP_NAME
Section = app_settings.get_extending_model()

@site.admin_view
@permission_required('%s.can_view_associated_content' % app_name)
def index(request):
    """
    Display a tree of section and subsection nodes.
    Because of the impossibility of expressing needed concepts (like recursion) 
    within the django template syntax, the tree html (nested <ul> elements) is
    constructed manually in this view using the get_rendered_tree and crawl
    functions.
    """
    roots = Section.get_root_nodes()
    node_list_html = '<ul id="node-list" class="treeview-red">'

    def get_rendered_tree(root_nodes, admin_links=[], html_class=None):
        html_class = html_class and 'class="%s"' % html_class or ""
        tree_html = "<ul%s>%s</ul>" % (
            html_class,
            "".join(map(crawl, root_nodes))        
        )
        return tree_html

    def crawl(node, admin_links=[]):
        link_html = app_settings.LINK_HTML
        link_list =  " " + " | ".join(
            [link_html[l] % node.pk for l in admin_links]
        )
        if node.is_leaf():
            return "<li><a href=\"edit/%s/\"><span>%s</span></a>%s</li>" % (
                node.pk,
                node.title, 
                link_list
            )
        else:
            children = node.get_children()
            html = "<li><a href=\"edit/%s/\"><span>%s</span></a>%s<ul>" % (
                node.pk,
                node.title, 
                link_list
            )        
            html += "".join(
                map(partial(crawl, admin_links=admin_links), children)
            )
            return html + "</ul></li>"


    crawl_add_links = partial(
        crawl, 
        admin_links=['add_link','del_link', 'list_link','order_link']
    )
    node_list_html += "".join(map(crawl_add_links, roots))
    node_list_html += (
        '<li><a class="addlink" href="add-to/root/">'
        'Add top-level section</a></li>'
    )
    node_list_html += "</ul>"
    return simple.direct_to_template(request, 
        template = "scaffold/admin/index.html",
        extra_context = {'node_list':node_list_html, 'title': "Edit Sections"}
    )


@transaction.commit_manually
@site.admin_view
@permission_required('%s.add_section' % app_name)
def add_to(request, section_id):
    """
    This view allows the user to create new Sections within the section tree. 
    Creation and editing of new sections, although involving the modelform 
    SectionForm, do not use it's save method. This is because the Section model 
    inherits from django-treebeard's MP_Node, which has its own methods for new 
    node creation.
    """
    if section_id == 'root':
        parent = None
    else:
        parent = Section.objects.get(pk=section_id)
        setattr(parent, 'has_children', len(parent.get_children()) > 0)
    if request.method == 'POST':
        section_form = SectionForm(request.POST, request.FILES)
        if section_form.is_valid():
            sec_kwargs = {}
            for field in section_form._meta.fields:
                sec_kwargs[field] = getattr(section_form.cleaned_data, field)
            if parent:
                section = parent.add_child(**section_kwargs)
            else:
                section = Section.add_root(**section_kwargs)
            source_formset = SourceFormSet(request.POST, instance=section)
            if source_formset.is_valid():
                source_formset.save()              
            # Now position node if necessary:
            if request.POST.get('position') and request.POST.get('child'):
                node = Section.objects.get(slug=form.cleaned_data['slug'])
                rel_to = get_object_or_404(Section, 
                    pk=request.POST.get('child')
                )
                rel = request.POST.get('position')
                pos_map = {
                    'before': 'left',
                    'after': 'right'
                }
                if rel not in pos_map.keys():
                    transaction.rollback()
                    positions = ", ".join(pos_map.keys())
                    return HttpResponseBadRequest((
                        "Position must be one of: " + 
                        positions
                    )) 
                try:
                    node.move(rel_to, pos_map[rel])
                except Exception, e:
                    transaction.rollback()
                    return HttpResponseServerError("Unable to move: " + e)
                else:
                    transaction.commit()
            else: 
                transaction.commit()
            return simple.redirect_to(request,
                url=reverse("sections:node_index"), 
                permanent=False
            )
    else:
        section_form = SectionForm()
        source_formset = SourceFormSet()
    return simple.direct_to_template(request, 
        template = "sections/admin/add.html",
        extra_context = {
            'node': parent,
            'section_form': section_form,
            'source_formset': source_formset,
            'title': "New %s" % (parent and "subsection" or "section")
        }
    )

def delete(request):
    pass

def edit(request):
    pass

def order_all_content(request):
    pass

def related_content(request):
    pass
    
def move(request):
    pass