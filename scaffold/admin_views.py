from copy import copy
import operator
from functools import partial

from django.contrib.auth.decorators import permission_required
from django.contrib.admin import site
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse, NoReverseMatch
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, \
    HttpResponseServerError
from django.shortcuts import get_object_or_404
from django.views.generic import simple

from forms import SectionForm
import settings as app_settings

app_name =  app_settings.EXTENDING_APP_NAME
allow_associated_ordering = app_settings.ALLOW_ASSOCIATED_ORDERING
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
    link_html = _get_user_link_html(request)
    node_list_html = '<ul id="node-list" class="treeview-red">'

    def get_rendered_tree(root_nodes, admin_links=[], html_class=None):
        html_class = html_class and 'class="%s"' % html_class or ""
        tree_html = "<ul%s>%s</ul>" % (
            html_class,
            "".join(map(crawl, root_nodes))        
        )
        return tree_html

    def crawl(node, admin_links=[]):
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
        admin_links=link_html.keys()
    )
    node_list_html += "".join(map(crawl_add_links, roots))
    if link_html.has_key('add_link'):        
        node_list_html += (
            '<li><a class="addlink" href="add-to/root/">'
            'Add a top-level section.</a></li>'
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
    commit_transaction = False
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
            # Position node if necessary.
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
                    commit_transaction = True
            else: 
                commit_transaction = True
            if commit_transaction:
                # Log that a section has been successfully added before
                # committing transaction.
                sections_admin = _get_admin_site()
                sections_admin and sections_admin.log_addition(request, node)
                transaction.commit()
            else:
                transaction.rollback()
            return simple.redirect_to(request,
                url=reverse("sections:sections_index"), 
                permanent=False
            )
    else:
        section_form = SectionForm()
        commit_transaction = True
        
    if commit_transaction:
        transaction.commit()
    else:
        transaction.rollback()
    return simple.direct_to_template(request, 
        template = "scaffold/admin/add.html",
        extra_context = {
            'parent': parent,
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
    section_repr = section.title
    if request.method == 'POST':
        section.delete()
        # Log that a section has been successfully deleted.
        sections_admin = _get_admin_site()
        sections_admin and \
            sections_admin.log_deletion(request, section, section_repr)
        # Redirect to sections index page.
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
    rel_sort_key = allow_associated_ordering and 'order' or None
    if request.method == 'POST':
        section_form = SectionForm(request.POST, request.FILES,
            instance=section
        )
        if section_form.is_valid():
            section = section_form.save()
            # Log that a section has been successfully edited.
            sections_admin = _get_admin_site()
            sections_admin and sections_admin.log_change(
                request, 
                section, 
                "%s edited." % section.title
            )
            # Redirect to sections index page.
            return simple.redirect_to(request,
                url=reverse("sections:sections_index"), 
                permanent=False
            )         
    else:
        section_form = SectionForm(instance=section)           
    content_type_id = ContentType.objects.get_for_model(Section).id
    return simple.direct_to_template(request, 
        template = "scaffold/admin/edit.html",
        extra_context = {
            'section': section,
            'content_type_id': content_type_id,
            'form': section_form,
            'title': "Edit %s '%s'" % (section.type, section.title),
            'related_content': _get_content_table(section, 
                sort_key=rel_sort_key
            ),
            'allow_associated_ordering': allow_associated_ordering,
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
            transaction.rollback()
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
            # Log that a section has been successfully moved.
            sections_admin = _get_admin_site()
            sections_admin and sections_admin.log_change(
                request, 
                section, 
                "%s moved." % section.title
            )
            # Redirect to sections index page.
            return simple.redirect_to(request,
                url=reverse("sections:sections_index"), 
                permanent=False
            )
    # Exclude the node from the list of candidates...
    other_secs = Section.objects.exclude(pk=section_id)
    # ...then exclude descendants of the node being moved.
    other_secs = [n for n in other_secs if not n.is_descendant_of(section)]
    
    # Provides a sections tree for user reference.
    def crawl(node):
        html_class = node.pk == section.pk and ' class="active"' or ""
        if node.is_leaf():
            return "<li%s>%s</li>" % (html_class, node.title)
        else:
            children = node.get_children()
            html = "<li%s>%s<ul>" % (html_class, node.title)      
            html += "".join(
                map(crawl, children)
            )
            return html + "</ul></li>"
    root_nodes = Section.get_root_nodes()
    tree_html = '<ul id="node-list" class="treeview-red">%s</ul>'
    tree_html = tree_html % ("".join(map(crawl, root_nodes)))
    return simple.direct_to_template(request, 
        template = "scaffold/admin/move.html",
        extra_context = {
            'section': section,
            'tree': other_secs,
            'title': "Move %s '%s'" % (section.type, section.title),
            'preview': tree_html
        }
    )

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
    content_table = _get_content_table(section)
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
    # If page request is out of range, deliver last page of results.
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
            'title': "'%s' %s related content" % (section.title, section.type),
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
    if not allow_associated_ordering:
        return simple.redirect_to(request,
            url=reverse("sections:edit", kwargs={'section_id': section.id}), 
            permanent=False
        )        
    content_table = _get_content_table(section, sort_key='order')
    if request.method == 'POST':
        for item, date, app, model, rel, edit_url in content_table:
            item_id = "%s-%s-%s" % (app, model, str(item.pk))
            item_order = request.POST.get(item_id, None)
            if item_order and item_order.isdigit():
                item.order = int(item_order)
                item.save()
            else:
                return HttpResponseBadRequest((
                    "Item order was not specified for every item, or the "
                    "order provided was not a number."
                ))
        # Log that a section has been successfully edited.
        section_admin = site._registry[Section]
        section_admin.log_change(
            request, 
            section, 
            "Content for %s reordered ." % section.title
        )
        # Redirect to sections index page.     
        return simple.redirect_to(request,
            url=reverse("sections:edit", kwargs={'section_id': section.id}), 
            permanent=False
        )        
    return simple.direct_to_template(request, 
        template = "scaffold/admin/order_all_content.html",
        extra_context = {
            'section': section,
            'related_content': content_table,
            'title': "Order Content for the %s \"%s\"" % (
                section.type, 
                section.title, 
            )
        }
    )

def _get_content_table(section, sort_key=None):
    """
    Not a view function; returns list of tuples containing:
    
    * the related object
    * its date (from get_latest_by prop, if it's set)
    * the application the object belongs to
    * the model the object belongs to
    * The type of relationship 
    * the URL in the admin that will allow you to edit the object
    
    """
    related_content = section.get_associated_content(sort_key=sort_key)
    content_table = []
    for item, app, model, relationship_type in related_content:
        edit_url = "admin:%s_%s_change" % (app, model.lower())
        try:
            edit_url = reverse(edit_url, args=[item.id])
        except:
            edit_url = "%s:edit" % app
            edit_url = reverse(edit_url, kwargs={'section_id': item.id})
        if item._meta.get_latest_by:
            date = getattr(item, item._meta.get_latest_by)
        else:
            date = None
        content_table.append((
             item, 
             date, 
             app, 
             model, 
             relationship_type, 
             edit_url
        ))
    return content_table

def _get_user_link_html(request):
    link_html = copy(app_settings.LINK_HTML)
    app_label = Section._meta.app_label
    Section._meta.get_add_permission()
    add_perm = app_label + "." + Section._meta.get_add_permission()
    del_perm = app_label + "." + Section._meta.get_delete_permission()
    if not request.user.has_perm(add_perm):
        del link_html['add_link']
    if not request.user.has_perm(del_perm):
        del link_html['del_link']
    return link_html

def _get_admin_site():
    """
    A utility function for getting the ModelAdmin instance for sections.
    Note that, if being run under the test runner, the ModelAdmin won't be
    available, in which case this function returns None. 
    """
    if site._registry.has_key(Section):
        return site._registry[Section]
    return None