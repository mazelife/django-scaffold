import operator
from functools import partial

from django.contrib.auth.decorators import permission_required
from django.contrib.admin import site
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, \
    HttpResponseServerError
from django.shortcuts import get_object_or_404
from django.views.generic import simple

from forms import SectionForm
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
            section_kwargs = {}
            for field in section_form.fields.keys():
                section_kwargs[field] = section_form.cleaned_data[field]
            if parent:
                section = parent.add_child(**section_kwargs)
            else:
                section = Section.add_root(**section_kwargs)         
            # Now position node if necessary:
            if request.POST.get('position') and request.POST.get('child'):
                node = Section.objects.get(
                    slug=section_form.cleaned_data['slug']
                )
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
                url=reverse("sections:sections_index"), 
                permanent=False
            )
    else:
        section_form = SectionForm()
    return simple.direct_to_template(request, 
        template = "scaffold/admin/add.html",
        extra_context = {
            'node': parent,
            'section_form': section_form,
            'title': "New %s" % (parent and "subsection" or "section")
        }
    )

@site.admin_view
@permission_required('%s.delete_section' % app_name)
def delete(request, section_id):
    """
    This view allows the user to delete Sections within the node tree.
    """
    section = get_object_or_404(Section, pk=section_id)
    if request.method == 'POST':
        section.delete()
        return simple.redirect_to(request,
            url=reverse("sections:sections_index"), 
            permanent=False
        )        
    return simple.direct_to_template(request, 
        template = "scaffold/admin/delete.html",
        extra_context = {
            'section': section, 
            'title': "Delete %s '%s'" % (section.type, section.title)
        }
    )

@site.admin_view
@permission_required('%s.change_section' % app_name)
def edit(request, section_id):
    """
    This view allows the user to edit Sections within the tree.
    """
    section = get_object_or_404(Section, pk=section_id)
    if request.method == 'POST':
        section_form = SectionForm(request.POST, request.FILES,
            instance=section
        )
        if section_form.is_valid():
            section = section_form.save()
            return simple.redirect_to(request,
                url=reverse("sections:sections_index"), 
                permanent=False
            )         
    else:
        section_form = SectionForm(instance=section)           
    return simple.direct_to_template(request, 
        template = "scaffold/admin/edit.html",
        extra_context = {
            'section': section, 
            'form': section_form,
            'title': "Edit %s '%s'" % (section.type, section.title),
            'fk_related_items': section.get_associated_content()
        }
    )

@transaction.commit_manually
@permission_required('%s.change_section' % app_name)
def move(request, section_id):
    """
    This view allows a user to move a Section within the node tree.
    """
    section = Section.objects.get(pk=section_id)
    if request.method == 'POST':
        rel = request.POST.get('relationship')
        if request.POST.get('to') == 'TOP':
            rel_to = Section.get_root_nodes()[0]
            rel = 'top'
        else:    
            rel_to = get_object_or_404(Section, pk=request.POST.get('to'))
        if rel_to.pk == section.pk:
            return HttpResponseBadRequest(
            "Unable to move node relative to itself."
            )
        pos_map = {
            'top': 'left',
            'neighbor': 'right',
            'child': 'first-child'
        }
        if rel not in pos_map.keys():
            return HttpResponseBadRequest(
                "Position must be one of %s " % ", ".join(pos_map.keys())
            )
        try:
            section.move(rel_to, pos_map[rel])
        except Exception, e:
            transaction.rollback()
            return HttpResponseServerError("Unable to move node. %s" % e)
        else:
            if Section.find_problems()[4] != []:
                Section.fix_tree()
            transaction.commit()
            return simple.redirect_to(request,
                url=reverse("sections:sections_index"), 
                permanent=False
            )
    other_secs = Section.objects.exclude(pk=section_id)
    # Exclude descendants of the node being moved:
    other_secs = [n for n in other_secs if not n.is_descendant_of(section)]
    return simple.direct_to_template(request, 
        template = "scaffold/admin/move.html",
        extra_context = {
            'section': section,
            'tree': other_secs,
            'title': "Move %s '%s'" % (section.type, section.title)
        }
    )


def order_all_content(request):
    pass

@site.admin_view
@permission_required('%s.can_view_associated_content' % app_name)
def related_content(request, section_id, list_per_page=10):
    """
    This view shows all content associated with a particular section. The edit 
    view also shows this info, but this view is for people who may not have 
    permissions to edit sections but still need to see all content associated
    with a particular Section.
    """
    section = get_object_or_404(Section, id=section_id)
    related_content = section.get_related_content()
    content_table = []
    for item, app, model, relationship_type in related_content:
        edit_url = "admin:%s_%s_change" % (app, model.lower())
        edit_url = reverse(edit_url, args=[item.id])
        if item._meta.get_latest_by:
            date = getattr(item, item._meta.get_latest_by)
        else:
            date = None
        content_table.append((
            item, 
            date, 
            app, 
            model, 
            relationship_type, edit_url
        ))
    sort = request.GET.get('sort')
    sort_map = {
        'name': 0,
        'date': 1,
        'content': 3
    }
    if sort and sort in sort_map.keys():
        content_table = sorted(
            content_table, 
            key=operator.itemgetter(sort_map[sort])
        )
    paginated_content = Paginator(content_table, list_per_page)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    # If page request is out of range, deliver last page of results:
    try:
        content_table = paginated_content.page(page)
    except (EmptyPage, InvalidPage):
        content_table = paginated_content.page(paginated_content.num_pages)
    return simple.direct_to_template(request, 
        template = "scaffold/admin/related_content.html",
        extra_context = {
            'section': section,
            'sort': sort,
            'related_content': content_table,
            'title': "'%s' %s Related Content" % (section.title, section.type),
        }
    )

@site.admin_view
@permission_required('%s.change_section' % app_name)
def order_all_content(request, section_id):
    """
    This view shows all content associated with a particular section including
    subsections, but unlike related_content, this view allows users to set the
    order of a particular section.
    """    
    section = get_object_or_404(Section, id=section_id)
    all_children = section.get_associated_content(sort_key='order')
    content_table = []
    for item in all_children:
        app = item._meta.app_label
        model = item._meta.object_name 
        if item._meta.get_latest_by:
            date = getattr(item, item._meta.get_latest_by)
        else:
            date = None
        content_table.append((item, date, app, model, item.order))
    if request.method == 'POST':
        resorted_content = []
        for item, date, app, model, current_order in content_table:
            item_id = "%s-%s-%s" % (app, model, str(item.pk))
            item_order = request.POST.get(item_id, None)
            if item_order and item_order.isdigit():
                current_order = int(item_order)
                item.order = current_order
                item.save()
            else:
                return HttpResponseBadRequest((
                    "Item order was not specified for every item, or the "
                    "order provided was not a number."
                ))
            resorted_content.append((item, date, app, model, item.order))
        content_table = resorted_content
        return simple.redirect_to(request,
            url=reverse("sections:sections_index"), 
            permanent=False
        )        
    content_table = sorted(
        content_table, 
        key=operator.itemgetter(4)
    )
    return simple.direct_to_template(request, 
        template = "scaffold/admin/order_all_content.html",
        extra_context = {
            'section': section,
            'related_content': content_table,
            'title': "'%s' %s Related Content" % (section.title, section.type),
        }
    )    
