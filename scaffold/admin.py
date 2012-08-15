from __future__ import with_statement

from copy import copy
from functools import partial
import operator

from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.admin.util import unquote
from django.core.exceptions import PermissionDenied, ValidationError, FieldError
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.core.urlresolvers import reverse, NoReverseMatch
from django.db import models, transaction
from django.forms.formsets import all_valid
from django.http import HttpResponseBadRequest, HttpResponseServerError, Http404
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_unicode
from django.forms.util import ErrorList
from django.utils.functional import update_wrapper
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.views.generic import simple

from forms import SectionForm
import app_settings

app_name =  app_settings.EXTENDING_APP_NAME
allow_associated_ordering = app_settings.ALLOW_ASSOCIATED_ORDERING
model_proxy = app_settings.get_extending_model()

csrf_protect_m = admin.options.csrf_protect_m

class SectionAdmin(admin.ModelAdmin):

    class Media:
        css = {
            "all": ("scaffold/styles/scaffold-admin.css",)
        }

    form = SectionForm
    list_per_page = 10
    template_base = "scaffold/admin/"
    prepopulated_fields = {"slug": ("title",)}

    change_form_template ="scaffold/admin/change_form.html"

    def get_urls(self):

        from django.conf.urls.defaults import patterns, url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        urls = super(SectionAdmin, self).get_urls()
        info = self.model._meta.app_label, self.model._meta.module_name
        return patterns('',
            url(r'^(.+)/create/$',
                wrap(self.custom_add_view),
                name='%s_%s_create' % info),
            url(r'^(.+)/move/$',
                wrap(self.move_view),
                name='%s_%s_move' % info),
            url(r'^(.+)/related/$',
                wrap(self.related_content_view),
                name='%s_%s_related' % info),
            url(r'^(.+)/order/$',
                wrap(self.order_content_view),
                name='%s_%s_order' % info),
        ) + urls

    def has_view_permission(self, request):
        """
        Returns True if the given request has permission to view the given
        Django model instance.

        If `obj` is None, this should return True if the given request has
        permission to change *any* object of the given type.
        """
        opts = self.opts
        return request.user.has_perm((
            opts.app_label + '.can_view_associated_content'
        ))

    @property
    def app_context(self):
        """
        Returns a dictionary containing the app name, model name, plural model
        name and changelist (index) url.
        """
        meta = self.model._meta
        return {
            'app_index_url': reverse('admin:app_list', args=(meta.app_label,)),
            'app_label': meta.app_label,
            'module_label': meta.module_name,
            'model_label': meta.verbose_name,
            'model_label_plural': unicode(meta.verbose_name_plural),
            'changelist_url': reverse('admin:%s_%s_changelist' %
            (meta.app_label, meta.module_name)),
        }

    def render_scaffold_page(self, request, template, context):
        """
        Helper function to render a scaffold admin page.
        """
        context.update(self.app_context)
        template_path = self.template_base + template
        return simple.direct_to_template(request,
            template = template_path,
            extra_context = context
        )

    def redirect_to_scaffold_index(self, request):
        """Redirect to the change list page of your model."""
        redirect_url = reverse(
            'admin:%(app_label)s_%(module_label)s_changelist'
            % self.app_context
        )
        return simple.redirect_to(request,
            url=redirect_url,
            permanent=False
        )

    def redirect_to_object_changeform(self, request, obj):
        """Redirect to the change form of the given object."""
        redirect_url = reverse(
            'admin:%(app_label)s_%(module_label)s_change' % self.app_context,
             args=(obj.pk,)
        )
        return simple.redirect_to(request,
            url=redirect_url,
            permanent=False
        )

    def get_changelist_repr(self, node):
        """
        A method that takes a node in the tree and returns a string
        representation for the changelist view.
        """
        html = '<span><a href="%s">%s <small> &ndash; /%s/</small></a></span>'
        return html % (node.get_absolute_url(), node.title, node.full_path)

    def changelist_view(self, request):
        """
        Display a tree of section and subsection nodes.
        Because of the impossibility of expressing needed concepts (e.g.
        recursion) within the django template syntax, the tree html (nested
        <ul> elements) is constructed manually in this view using the crawl
        function.
        """
        model = self.model

        if not self.has_view_permission(request):
            raise PermissionDenied

        roots = model.get_root_nodes()
        link_html = _get_user_link_html(request)
        link_html_fields = [name for name, html in link_html]
        link_html_dict = dict(link_html)

        def crawl(node, admin_links=[]):
            """
            Nests a series of treebeard nodes in unordered lists
            """
            # Generate HTML for the current node
            html = (
                '<li id="node-%s">%s<div class="links">%s</div>'
            ) % (
                node.id,
                self.get_changelist_repr(node),
                " ".join([link_html_dict[l] % node.pk for l in admin_links])
            )
            # Inject submenu of children, if applicable
            if not node.is_leaf():
                children = node.get_children()
                children = "".join(
                    map(partial(crawl, admin_links=admin_links), children)
                )
                html += "<ul>%s</ul>" % children

            return html + "</li>"

        crawl_add_links = partial(
            crawl,
            admin_links=link_html_fields
        )

        # Generate HTML
        node_list_html = '<ul id="node-list">'
        node_list_html += "".join(map(crawl_add_links, roots))
        node_list_html += "</ul>"

        context = {
            'node_list':node_list_html,
            'title': "Edit %s" % self.app_context['model_label_plural']
        }
        return self.render_scaffold_page(request, 'index.html', context)

    def add_view(self, request):
        """
        This view will not be used because adding of nodes to the tree can
        never be done without context (i.e. where in the tree the new node is
        to be positioned). Therefore, the "add" links that appear on the index
        of the admin site will not work, hence this redirect to the model
        changeform when it's clicked.
        """
        return self.redirect_to_scaffold_index(request)

    def custom_add_view(self, request, section_id,
        form_url='', extra_context=None):
        """
        The 'add' admin view for this model.

        We're managing transactions manually on this one because of the way
        treebeard works. Treebeard wraps a model's save method and doesn't allow
        us to pass the `commit=False` argument to the save method. But the
        admin wants to do this because creation of the model depends on also
        being able validate and save any inlines. Treebeard does however use the
        `transaction.commit_unless_managed()` feature in it's save wrappers.

        We can exploit this to safely unwind the creation of all objects if
        something fails along the way.

        """
        model = self.model
        opts = model._meta

        if not self.has_add_permission(request):
            raise PermissionDenied
        if section_id == 'root':
            parent = None
        else:
            parent = model.objects.get(pk=section_id)
            setattr(parent, 'has_children', len(parent.get_children()) > 0)

        ModelForm = self.get_form(request)
        formsets = []
        if request.method == 'POST':
            with transaction.commit_manually():
                # Becuase transactions are managed manually, any DB
                # or validation operation that occurs durint the processing of a
                # POST request will raise a ValidationError exception if it
                # encounters a problem. The giant try/catch block which wraps
                # all this allows us to rollback if any problems occur.
                try:
                    form = ModelForm(request.POST, request.FILES)
                    if form.is_valid():
                        try:
                            kwargs = form.cleaned_data
                            new_object = self.validate_and_create_object(
                                parent,
                                kwargs
                            )
                            form_validated = True
                        except ValidationError, e:
                            # Validation can't happen via the usual channels, so
                            # we're going to monkey with the form's error list.
                            form_validated = False
                            form._errors['slug'] = ErrorList()
                            form._errors['slug'].append(e.messages[0])
                            new_object = self.model()
                        except Exception, e:
                            # Something bad has happened; not sure what, so we'll
                            # punt by re-raising as a FieldError which will be
                            # handled by the outer try/catch.
                            raise FieldError, e
                    else:
                        form_validated = False
                        new_object = self.model()
                    prefixes = {}
                    inline_instances = self.get_inline_instances(request)
                    for FormSet, inline in\
                        zip(self.get_formsets(request), inline_instances):
                        prefix = FormSet.get_default_prefix()
                        prefixes[prefix] = prefixes.get(prefix, 0) + 1
                        if prefixes[prefix] != 1:
                            prefix = "%s-%s" % (prefix, prefixes[prefix])
                        formset = FormSet(
                            data=request.POST,
                            files=request.FILES,
                            instance=new_object,
                            save_as_new=request.POST.has_key("_saveasnew"),
                            prefix=prefix,
                            queryset=inline.queryset(request)
                        )
                        formsets.append(formset)
                    if all_valid(formsets) and form_validated:
                        # The object validated and saved, the inlines appear to
                        # be valid, now we will save them one by one:
                        try:
                            for formset in formsets:
                                self.save_formset(request, form, formset,
                                    change=False
                                )
                        except Exception, e:
                            raise ValidationError, e
                        if form_validated and request.POST.get('position') \
                            and request.POST.get('child'):
                            try:
                                rel_to = model.objects.get(
                                    pk=request.POST.get('child')
                                )
                            except model.DoesNotExist, e:
                                raise ValidationError, e
                            rel = request.POST.get('position')
                            pos_map = {
                                'before': 'left',
                                'after': 'right'
                            }
                            if rel not in pos_map.keys():
                                positions = ", ".join(pos_map.keys())
                                raise ValidationError, (
                                    "Position must be one of: %s" %
                                    positions
                                )
                            try:
                                new_object.move(rel_to, pos_map[rel])
                            except Exception, e:
                                e = str(e)
                                raise ValidationError, "Unable to move: %s" % e

                        self.log_addition(request, new_object)
                        transaction.commit()
                        if request.POST.has_key("_continue"):
                            return self.redirect_to_object_changeform(
                                request,
                                new_object
                            )
                        return self.redirect_to_scaffold_index(request)
                    else:
                        # Fieldset validation error, so we rollback
                        transaction.rollback()
                except ValidationError, e:
                        transaction.rollback()
                        return HttpResponseBadRequest(" ".join(e.messages))
        else:         # Request is not POST

            # Prepare the dict of initial data from the request.
            # We have to special-case M2Ms as a list of comma-separated PKs.
            initial = dict(request.GET.items())
            for k in initial:
                try:
                    f = opts.get_field(k)
                except models.FieldDoesNotExist:
                    continue
                if isinstance(f, models.ManyToManyField):
                    initial[k] = initial[k].split(",")
            form = ModelForm(initial=initial)
            prefixes = {}
            inline_instances = self.get_inline_instances(request)
            for FormSet, inline in zip(self.get_formsets(request), inline_instances):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(instance=self.model(), prefix=prefix,
                                  queryset=inline.queryset(request))
                formsets.append(formset)

        adminForm = helpers.AdminForm(form, list(self.get_fieldsets(request)),
            self.prepopulated_fields, self.get_readonly_fields(request),
            model_admin=self)
        media = self.media + adminForm.media

        inline_admin_formsets = []
        inline_instances = self.get_inline_instances(request)
        for inline, formset in zip(inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request))
            readonly = list(inline.get_readonly_fields(request))
            inline_admin_formset = helpers.InlineAdminFormSet(inline, formset,
                fieldsets, readonly, model_admin=self)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media

        context = {
            'add': True,
            'parent': parent,
            'title': _('Add %s') % force_unicode(opts.verbose_name),
            'adminform': adminForm,
            'is_popup': request.REQUEST.has_key('_popup'),
            'show_delete': False,
            'media': mark_safe(media),
            'inline_admin_formsets': inline_admin_formsets,
            'errors': helpers.AdminErrorList(form, formsets),
            'app_label': opts.app_label,
        }
        context.update(extra_context or {})
        return self.render_scaffold_page(request, "add.html", context)

    @csrf_protect_m
    @transaction.commit_on_success
    def delete_view(self, request, object_id):
        """
        This view allows the user to delete Sections within the node tree.
        """
        model = self.model

        try:
            obj = model.objects.get(pk=object_id)
        except model.DoesNotExist:
            # Don't raise Http404 just yet, because we haven't checked
            # permissions yet. We don't want an unauthenticated user to be able
            # to determine whether a given object exists.
            obj = None
        if not self.has_delete_permission(request, obj):
            raise PermissionDenied
        if not obj:
            raise
        if request.method == 'POST':
            obj.delete()
            # Log that a section has been successfully deleted.
            self.log_deletion(request, obj, obj.title)
            return self.redirect_to_scaffold_index(request)
        context = {
            'obj': obj,
            'title': "Delete %s" % self.app_context['model_label']
        }
        return self.render_scaffold_page(request,
            "delete.html", context
        )
    delete_view = transaction.commit_on_success(delete_view)

    @csrf_protect_m
    @transaction.commit_on_success
    def move_view(self, request, object_id):
        """This view allows the user to move sections within the node tree."""
        #FIXME: should be an AJAX responder version of this view.

        model = self.model
        opts = model._meta

        try:
            obj = self.queryset(request).get(pk=unquote(object_id))
        except model.DoesNotExist:
            # Don't raise Http404 just yet, because we haven't checked
            # permissions. We don't want an unauthenticated user to be able
            # to determine whether a given object exists.
            obj = None
        if not self.has_change_permission(request, obj):
            raise PermissionDenied
        if obj is None:
            raise Http404(_(
                '%(name)s object with primary key %(key)r does not exist.') % {
                    'name': force_unicode(opts.verbose_name),
                    'key': escape(object_id)
            })

        if request.method == 'POST':
            rel = request.POST.get('relationship')
            if request.POST.get('to') == 'TOP':
                rel_to = obj.get_root_nodes()[0]
                rel = 'top'
            else:
                rel_to = get_object_or_404(model,
                    pk=request.POST.get('to')
                )
            if rel_to.pk == obj.pk:
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
                obj.move(rel_to, pos_map[rel])
            except Exception, e:
                return HttpResponseServerError("Unable to move node. %s" % e)
            else:
                if model.find_problems()[4] != []:
                    model.fix_tree()
                # Log that a section has been successfully moved.
                change_message = "%s moved." % obj.title
                self.log_change(request, obj, change_message)
                # Redirect to sections index page.
                return self.redirect_to_scaffold_index(request)
        # Exclude the node from the list of candidates...
        other_secs = model.objects.exclude(pk=object_id)
        # ...then exclude descendants of the node being moved.
        other_secs = [n for n in other_secs if not n.is_descendant_of(obj)]

        # Provides a sections tree for user reference.
        def crawl(node):
            html_class = node.pk == obj.pk and ' class="active"' or ""
            if node.is_leaf():
                return "<li%s>%s</li>" % (html_class, node.title)
            else:
                children = node.get_children()
                html = "<li%s>%s<ul>" % (html_class, node.title)
                html += "".join(
                    map(crawl, children)
                )
                return html + "</ul></li>"
        root_nodes = self.model.get_root_nodes()
        tree_html = '<ul id="node-list" class="treeview-red">%s</ul>'
        tree_html = tree_html % ("".join(map(crawl, root_nodes)))
        context = {
            'obj': obj,
            'tree': other_secs,
            'title': "Move %s" % self.app_context['model_label'],
            'preview': tree_html
        }
        return self.render_scaffold_page(request,
            "move.html", context
        )
    move_view = transaction.commit_on_success(move_view)

    @csrf_protect_m
    @transaction.commit_on_success
    def change_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, unquote(object_id))
        if not obj:
            model_name = self.model._meta.module_name.title()
            raise Http404, "%s not found." % model_name
        rel_sort_key = allow_associated_ordering and 'order' or None
        context = {
            'allow_associated_ordering': allow_associated_ordering,
            'related_content': _get_content_table(obj, sort_key=rel_sort_key)
        }
        context.update(self.app_context)
        context.update(extra_context or {})
        return super(SectionAdmin, self).change_view(request, object_id,
            extra_context=context
        )

    def related_content_view(self, request, section_id, list_per_page=10):
        """
        This view shows all content associated with a particular section. The
        edit view also shows this info, but this view is for people who may not
        have permissions to edit sections but still need to see all content
        associated with a particular Section.
        """
        model = self.model

        try:
            obj = self.queryset(request).get(pk=unquote(section_id))
        except model.DoesNotExist:
            # Don't raise Http404 just yet, because we haven't checked
            # permissions. We don't want an unauthenticated user to be able
            # to determine whether a given object exists.
            obj = None
        if not self.has_view_permission(request):
            raise PermissionDenied
        content_table = _get_content_table(obj)
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
        context = {
            'obj': obj,
            'sort': sort,
            'related_content': content_table,
            'title': "Related %s content" % self.app_context['model_label'],
        }
        return self.render_scaffold_page(
            request,
            'related_content.html',
            context
        )

    @csrf_protect_m
    @transaction.commit_on_success
    def order_content_view(self, request, object_id):
        """
        This view shows all content associated with a particular section
        including subsections, but unlike related_content, this view allows
        users to set the order of a particular section.
        """
        model = self.model
        opts = model._meta

        try:
            obj = self.queryset(request).get(pk=unquote(object_id))
        except model.DoesNotExist:
            # Don't raise Http404 just yet, because we haven't checked
            # permissions. We don't want an unauthenticated user to be able
            # to determine whether a given object exists.
            obj = None
        if not self.has_change_permission(request, obj):
            raise PermissionDenied
        if obj is None:
            raise Http404(_(
                '%(name)s object with primary key %(key)r does not exist.') % {
                    'name': force_unicode(opts.verbose_name),
                    'key': escape(object_id)
            })
        if not app_settings.ALLOW_ASSOCIATED_ORDERING:
            return self.redirect_to_scaffold_index(request)
        content_table = _get_content_table(obj, sort_key='order')
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
            self.log_change(
                request,
                obj,
                "Content for %s reordered ." % obj.title
            )
            # Redirect to sections index page.
            return self.redirect_to_scaffold_index(request)
        context = {
            'obj': obj,
            'related_content': content_table,
            'title': "Order %s content" % self.app_context['model_label']
        }
        return self.render_scaffold_page(request, "order_all_content.html",
            context
        )

    def prep_m2m(self, kwargs):
        """
        Any kwargs which correspond to M2M fields on the model cannot be
        saved concurrently. This function removes those from the base kwargs
        and returns them separately so they can be added after the initial model
        is saved by treebeard.
        """
        m2m_rels = {}
        for field in self.model._meta.many_to_many:
            if field.name in kwargs:
                m2m_objects = kwargs.pop(field.name)
                m2m_rels[field.name] = m2m_objects
        return kwargs, m2m_rels

    def validate_and_create_object(self, parent, kwargs):
        """
        Based on the `VALIDATE_GLOBALLY_UNIQUE_SLUGS` setting, ensures that no
        other children with the slug exist *or* ensures that no other children
        at that level with the same slug exist. If that requirement is
        satisfied, creates and returns the object. Otherwise, a ValidationError
        is raised.

        This task, sadly, cannot be handled through traditional model or form
        validators because the model's save method is wrapped up in treebeard
        code.
        """
        slug = kwargs['slug']
        kwargs, m2m_data = self.prep_m2m(kwargs)
        verbose_name = self.model._meta.verbose_name
        if app_settings.VALIDATE_GLOBALLY_UNIQUE_SLUGS:
            try:
                self.model.objects.get(slug=slug)
            except self.model.DoesNotExist:
                if parent:
                    newobj = parent.add_child(**kwargs)
                else:
                    newobj = self.model.add_root(**kwargs)
                # Add any M2M related objects now.
                for field_name, related_objects in m2m_data.items():
                    m2m_manager = getattr(newobj, field_name)
                    m2m_manager.add(*related_objects)
                return newobj
            else:
                raise ValidationError, (
                    "A %s with the slug '%s' already exists"
                ) % (verbose_name, slug)
        # Validation if slugs do not have to be globally unique.
        else:
            if parent:
                if slug in [obj.slug for obj in parent.get_children()]:
                    err_str = (
                        "The %s '%s' already has a child with the "
                        "slug '%s.'"
                    ) % (verbose_name, parent.title, slug)
                    raise ValidationError, err_str
                else:
                    newobj = parent.add_child(**kwargs)
            else:
                if slug in [obj.slug for obj in \
                    self.model.get_root_nodes()]:
                    err_str = (
                        "A %s already exists at the root of the tree with "
                        "the slug %s."
                    ) % (verbose_name, slug)
                    verbose_name = self.model._meta.verbose_name
                    raise ValidationError, err_str
                else:
                    newobj = self.model.add_root(**kwargs)
            # Add any M2M related objects now.
            for field_name, related_objects in m2m_data.items():
                m2m_manager = getattr(newobj, field_name)
                m2m_manager.add(*related_objects)
            return newobj
        return None

######################################
#        Utility Functions
######################################


def _get_content_table(obj, sort_key=None):
    """
    Returns list of tuples containing:

    * the related object
    * its date (from get_latest_by prop, if it's set)
    * the application the object belongs to
    * the model the object belongs to
    * The type of relationship
    * the URL in the admin that will allow you to edit the object

    """
    related_content = obj.get_associated_content(sort_key=sort_key)
    content_table = []
    for item, app, model, relationship_type in related_content:
        edit_url = "admin:%s_%s_change" % (app, model.lower())
        try:
            edit_url = reverse(edit_url, args=[item.id])
        except NoReverseMatch:
            edit_url = None
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
    """
    Checks available user permissions to make sure that the rendered changelist
    page does not offer the user options which they don't have permissions for
    (avoids having a PermissionDenied exception get raised).
    """
    link_html = copy(app_settings.LINK_HTML)
    app_label = model_proxy._meta.app_label
    model_proxy._meta.get_add_permission()
    add_perm = app_label + "." + model_proxy._meta.get_add_permission()
    del_perm = app_label + "." + model_proxy._meta.get_delete_permission()
    if not request.user.has_perm(add_perm):
        link_html = [(name, html) for name, html in  link_html.items() \
            if name != 'add_link'
        ]
    if not request.user.has_perm(del_perm):
        link_html = [(name, html) for name, html in  link_html.items() \
            if name != 'del_link'
        ]
    return link_html