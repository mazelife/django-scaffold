from django.conf import settings
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.loading import cache
from django.template import Context, Template
from django.test import TestCase

from models import BaseSection

import app_settings

"""
Current test coverage
====================================================

A listing of code coverage by module.

Name                             Stmts   Exec  Cover
-----------------------------------------------------
scaffold.admin                     375    258    68%
scaffold.forms                       8      7    87%
scaffold.middleware                 51     35    68%
scaffold.models                     87     82    94%
scaffold.templatetags.sections      65     58    89%
scaffold.views                      19      9    47%
-----------------------------------------------------
TOTAL                              605    449    74%
"""

try:
    cache.get_app('admin')
    HAS_DJANGO_AUTH = True
except ImproperlyConfigured:
    HAS_DJANGO_AUTH = False

BASE_DATA = [
  {'data':{'slug': '1', 'title': '1', 'description':'1'}},
  {'data':{'slug': '2', 'title': '2', 'description':'2'}, 'children':[
    {'data':{'slug': '21', 'title': '21', 'description':'21'}},
    {'data':{'slug': '22', 'title': '22', 'description':'22'}},
    {'data':{'slug': '23', 'title': '23', 'description':'23'}, 'children':[
      {'data':{'slug': '231', 'title': '231', 'description':'231'}},
    ]},
    {'data':{'slug': '24', 'title': '24', 'description':''}},
  ]},
  {'data':{'slug': '3', 'title': '3', 'description':'3'}},
  {'data':{'slug': '4', 'title': '4', 'description':'4'}, 'children':[
    {'data':{'slug': '41', 'title': '41', 'description':'41'}},
  ]},
]

class TestSection(BaseSection):
    """ A model of a mock section object"""
    description = models.CharField(max_length=255, blank=True)


from admin import SectionAdmin
admin.site.register(TestSection, SectionAdmin)

class TestArticle(models.Model):
    """A mock object with an FK relationship to a section"""
    title = models.CharField(max_length=255)
    section = models.ForeignKey(TestSection)

    def __unicode__(self):
        return self.title

class BaseSortedTestArticle(models.Model):
    """A mock object with an FK relationship to a section"""
    title = models.CharField(max_length=255)
    section = models.ForeignKey(TestSection)

    class Meta:
        ordering = ['title']
        abstract = True

    def __unicode__(self):
        return self.title

class SortedTestArticle(BaseSortedTestArticle):
    pass

class OtherSortedTestArticle(BaseSortedTestArticle):
    pass

class SectionTest(TestCase):

    csrf_disabled = False
    test_user = 'testrunner'
    test_password = 'testrunner'

    def _patch_get_extending_model(self):
        # A little patching to make sure that get_extending_model() returns
        # TestSection.
        from scaffold import app_settings
        def get_test_model():
            return TestSection
        app_settings.get_extending_model = get_test_model
        from middleware import _build_section_path_map
        _build_section_path_map()

    def _disable_csrf_middleware(self):
        settings.MIDDLEWARE_CLASSES = filter(lambda m: 'CsrfMiddleware' \
            not in m, settings.MIDDLEWARE_CLASSES
        )
        self.csrf_disabled = True

    def _setup_admin(self):
        """Check to see if test runner user was already created (perhaps by
        another test case) and if not, create it.
        """
        try:
            User.objects.get(username=self.test_user)
        except User.DoesNotExist:
            user = User.objects.create_superuser(
                self.test_user,
                'test@localhost.com',
                self.test_password
            )
            user.save()
        # Install admin:
        admin_patterns = patterns(
            (r'^admin/', include(admin.site.urls)),
        )
        from urls import urlpatterns
        urlpatterns = admin_patterns + urlpatterns

    def _log_test_client_in(self, login_url=None):
        """Log the test client in using the test runner user"""
        self._setup_admin()
        if not login_url:
            from django.conf.global_settings import LOGIN_URL as login_url
        login_url = "/admin/login/"
        return self.client.login(
            username=self.test_user,
            password=self.test_password
        )

    def _log_test_client_out(self):
        """Log the test client out using the test runner user"""
        self.client.logout()

    @property
    def admin_index_url(self):
        self._patch_get_extending_model()
        opts = app_settings.get_extending_model()._meta
        return reverse(
            'admin:%s_%s_changelist' % (opts.app_label, opts.module_name)
        )

    def get_admin_urls(self, obj):
        self._patch_get_extending_model()
        opts = app_settings.get_extending_model()._meta
        prefix = "admin:%s_%s_" % (opts.app_label, opts.module_name)
        views = ('create', 'change','delete', 'move','related','order')
        arg = hasattr(obj, 'pk') and obj.pk or obj
        urls = {}
        for view in views:
            urls[view] = reverse(prefix + view, args=(arg,))
        urls['index'] = self.admin_index_url
        return urls

    def login_and_load(self):
        """Log client in and load sections data."""
        #import settings
        if not self.csrf_disabled:
            self._disable_csrf_middleware()
        self._log_test_client_in()
        TestSection.load_bulk(BASE_DATA)
        import admin
        admin.model_proxy = TestSection # Monkey patch!

    def test_admin_index(self):
        """
        Verify that each section in the section tree can be found on the admin
        index page and that it's title is present."""
        self.login_and_load()
        sections = TestSection.objects.all()
        response = self.client.get(self.admin_index_url)
        for section in sections:
            self.assertTrue(section.title in response.context['node_list'])

    def test_admin_section_create_move(self):
        """
        Via the admin interface, create a new section in the the tree under
        the "2" section and then move it to the "4" section as the last child.
        """
        # Try creating a root-level node.
        self.login_and_load()
        admin_urls = self.get_admin_urls('root')
        response = self.client.post(admin_urls['create'], {
            'slug': 'bazz',
            'title': 'Bazz',
        })
        # On sucess should redirect.
        self.assertRedirects(response, admin_urls['index'])
        self.assertTrue('bazz' in \
            [node.slug for node in TestSection.get_root_nodes()]
        )
        # Try creating a node that is a child
        test_section = TestSection.objects.get(slug="2")
        admin_urls = self.get_admin_urls(test_section)
        response = self.client.get(admin_urls['create'])
        self.assertContains(response, test_section.title)
        # Create a new section, but use a bad position:
        response = self.client.post(admin_urls['create'], {
            'slug': 'foobar',
            'title': 'Foo Bar',
            'position': 'beside',
            'child': '4'
        })
        self.assertEqual(response.status_code, 400)
        try:
            section = TestSection.objects.get(slug="foobar")
            section.delete()
        except TestSection.DoesNotExist:
            pass
        # Create a new section properly via the form and verify it exists.
        child_section = TestSection.objects.get(title="2")
        response = self.client.post(admin_urls['create'], {
            'slug': 'foobar',
            'title': 'Foo Bar',
            'description': 'Foo Bar description',
            'position': 'after',
            'child': str(child_section.pk)
        })
        # On sucess should redirect.
        self.assertRedirects(response, admin_urls['index'])
        # Verify new section exists and is child of the "2" section...
        self.assertTrue(len(TestSection.objects.filter(title="Foo Bar")) == 1)
        foobar = TestSection.objects.get(slug="foobar")
        self.assertTrue(foobar.is_root())
        self.assertEqual(child_section.get_next_sibling(), foobar)
        # Now move the section...
        admin_urls = self.get_admin_urls(foobar)
        response = self.client.get(admin_urls['move'])
        self.assertEqual(response.context['obj'].pk, foobar.pk)
        # ... first with an incorrect reltionship field...
        response = self.client.post(admin_urls['move'], {
            'relationship': 'sibling',
            'to': TestSection.objects.get(slug="4").id
        })
        self.assertEqual(response.status_code, 400)
        # ... then a correct one.
        response = self.client.post(admin_urls['move'], {
            'relationship': 'child',
            'to': TestSection.objects.get(slug="4").id
        })
        # On sucess should redirect to index.
        self.assertRedirects(response, admin_urls['index'])
        # Verify section moved where it was supposed to.
        self.assertEqual(
            TestSection.objects.get(slug="foobar").get_parent(),
            TestSection.objects.get(slug="4")
        )
        # Try moving a section to itself.
        response = self.client.post(admin_urls['move'], {
            'relationship': 'child',
            'to': foobar.id
        })
        self.assertEqual(response.status_code, 400)
        # Move section to root of tree.
        response = self.client.post(admin_urls['move'], {
            'relationship': 'neighbor',
            'to': 'TOP'
        })
        self.assertEqual(
            TestSection.get_root_nodes()[0].slug,
            foobar.slug
        )
        # Move it one more time.
        response = self.client.post(admin_urls['move'], {
            'relationship': 'neighbor',
            'to': TestSection.objects.get(slug="231").id
        })
        self.assertRedirects(response, admin_urls['index'])
        # Verify section moved where it was supposed to.
        self.assertEqual(
            [u'231', u'foobar'],
            [n.slug for n in TestSection.objects.get(slug="23").get_children()]
        )

    def test_admin_validation(self):
        """
        Make sure we can't create two sections with the same slug under one
        parent.
        """
        #FIXME: Write a test.
        self.login_and_load()
        test_section = TestSection.objects.get(slug="2")
        admin_urls = self.get_admin_urls(test_section)
        response = self.client.post(admin_urls['create'], {
            'slug': '22',
            'title': 'Invalid!',
        })
        err = response.context['adminform'].form.errors['slug'][0]
        self.assertEqual(
            u"Test section with this Slug already exists.",
            err
        )

    def test_admin_section_remove(self):
        """Delete a section via the admin interface."""
        self.login_and_load()
        test_section = TestSection.objects.get(slug="2")
        admin_urls = self.get_admin_urls(test_section)
        response = self.client.get(admin_urls['delete'])
        # Make sure we get a confirmation page that mentions child sections.
        self.assertContains(response, test_section.title)
        for child in test_section.get_children():
            self.assertContains(response, child.title)
        response = self.client.post(admin_urls['delete'])
        # Delete operation redirects to index.
        self.assertRedirects(response, admin_urls['index'])
        # Section and it's children are gone.
        self.assertTrue(len(TestSection.objects.filter(title="2")) == 0)

    def test_admin_section_edit(self):
        """Edit the a section via the admin interface."""
        self.login_and_load()
        test_section = TestSection.objects.get(slug="41")
        admin_urls = self.get_admin_urls(test_section)
        response = self.client.get(admin_urls['change'])
        self.assertEqual(response.context['original'].slug, test_section.slug)
        response = self.client.post(admin_urls['change'], {
            'slug': '41b',
            'title': 'Forty One B',
            'description': 'Description tktk.'
        })
        # Verify edit operation redirects to index.
        self.assertRedirects(response, admin_urls['index'])
        # New data is there:
        edited_section = TestSection.objects.get(slug="41b")
        self.assertTrue(edited_section.title == 'Forty One B')
        self.assertTrue(edited_section.description == 'Description tktk.')

    def test_admin_section_related(self):
        """View related content via the admin interface."""
        self.login_and_load()
        test_section = TestSection.objects.get(slug="41")
        admin_urls = self.get_admin_urls(test_section)
        response = self.client.get(admin_urls['related'])
        self.assertTrue(response.status_code == 200)
        #FIXME: this could use better tests.

    def test_admin_section_order_all_content(self):
        """View related content via the admin interface."""
        self.login_and_load()
        test_section = TestSection.objects.get(slug="41")
        admin_urls = self.get_admin_urls(test_section)
        response = self.client.get(admin_urls['related'])
        self.assertTrue(response.status_code == 200)
        #FIXME: this could use better tests.

    def test_model_get_related_content(self):
        """Test the BaseSection model's get_related_content method"""
        TestSection.load_bulk(BASE_DATA)
        section = TestSection.objects.get(slug='2')
        article = TestArticle(title='B Test Article', section=section)
        article.save()
        content = section.get_related_content()
        self.assertTrue(len(content) == 1)
        item, application, model_name, rel_type = content[0]
        self.assertTrue(item.title == u'B Test Article')
        self.assertTrue(application == 'scaffold')
        self.assertTrue(model_name == 'TestArticle')
        self.assertTrue(rel_type == 'foreign-key')
        for title in ['A Test Article', 'Z Test Article']:
            article = TestArticle(title=title, section=section)
            article.save()
        content = section.get_related_content(sort_fields=['title'])
        self.assertEqual(
            [item[0].title for item in content],
            [u'A Test Article', u'B Test Article', u'Z Test Article']
        )
        # Remove related content, create new content from two models so we
        # can test infer_sort property.
        for item in content:
            item[0].delete()
        for title in ['C', 'Y', 'J']:
            article = SortedTestArticle(title=title, section=section)
            article.save()
        for title in ['A', 'D', 'Z']:
            article = OtherSortedTestArticle(title=title, section=section)
            article.save()
        # Verify that get_related_content shuffles content together in alpha
        # order.
        content = section.get_related_content(infer_sort=True)
        self.assertEqual(
             [item[0].title for item in content],
             [u'A', u'C', u'D', u'J', u'Y', u'Z']
         )

    def test_model_get_associated_content(self):
        """Test the BaseSection model's get_associated_content method"""
        TestSection.load_bulk(BASE_DATA)
        section = TestSection.objects.get(slug='2')
        article = TestArticle(title='1 Test Article', section=section)
        article.save()
        content = section.get_associated_content()
        self.assertTrue(len(content) == 5)
        child_sections = [s for s in content if s[3] == 'subsection']
        self.assertEqual(len(section.get_children()), len(child_sections))
        for s in section.get_children():
            self.assertTrue(s.slug in [s[0].slug for s in child_sections])
        child_articles = [s for s in content if s[2] == 'TestArticle']
        self.assertTrue(len(child_articles) == 1)
        self.assertEqual(child_articles[0][0].title, '1 Test Article')
        # Test the get_associated_content with an "only" argument.
        content = section.get_associated_content(only=["scaffold.TestArticle"])
        self.assertTrue(len(content) == 1)
        self.assertEqual(content[0][0].title, '1 Test Article')
        # Test the get_associated_content with a "sort_key" argument.
        content = section.get_associated_content(sort_key='title')
        self.assertEqual(
            [c[0].title for c in content],
            [u'1 Test Article', u'21', u'22', u'23', u'24']
        )

    def test_model_get_subsections(self):
        """Test the BaseSection model's get_subsections method"""
        TestSection.load_bulk(BASE_DATA)
        section = TestSection.objects.get(slug='2')
        for sub_section in section.get_subsections():
            self.assertTrue(sub_section.slug in ['21','22','23','24'])

    def test_model_get_first_populated_field(self):
        """Test the BaseSection model's get_first_populated_field method"""
        TestSection.load_bulk(BASE_DATA)
        section = TestSection.objects.get(slug='24')
        self.assertEqual(
            section.get_first_populated_field('description'),
            '2'
        )
        section = TestSection.objects.get(slug='23')
        self.assertEqual(
            section.get_first_populated_field('description'),
            '23'
        )

    def test_templatetag_get_root_sections(self):
        """Test that the get_root_sections template tag works as expected."""
        TestSection.load_bulk(BASE_DATA)
        self._patch_get_extending_model()
        # Test basic version of template tag.
        template = Template("""{%load sections%}
        <ul>{% get_root_sections as root_sections %}
        {{root_sections|pprint}}
        {%for nav in root_sections%}<li>{{nav.title}}</li>{%endfor%}
        </ul>
        """)
        context = Context({})
        result = template.render(context)
        # Test extended version of template tag.
        for root in TestSection.get_root_nodes():
            self.assertTrue(root.title in result)
        template = Template("""{%load sections%}
        <ul>{% get_root_sections with subsection as root_sections %}
        {{root_sections|pprint}}
        {%for nav in root_sections%}
            <li{%if nav.is_active%} class="active"{%endif%}>{{nav.title}}</li>
        {%endfor%}
        </ul>
        """)
        context = Context({'subsection': TestSection.objects.get(slug='231')})
        result = template.render(context)
        for root in TestSection.get_root_nodes():
            self.assertTrue(root.title in result)
        self.assertTrue('<li class="active">2</li>' in result)

    def test_templatetag_section_is_descendant(self):
        """
        Test that the section_is_descendant template tag works as
        expected.
        """
        TestSection.load_bulk(BASE_DATA)
        template = Template("""{%load sections%}
        {% section_is_descendant subsection of rootsection as descends %}
        {% if descends%}Passes Test 1{%endif%}
        {% section_is_descendant orphan of rootsection as descends %}
        {% if descends%}{%else%}Passes Test 2{%endif%}
        """)
        context = Context({
            'subsection': TestSection.objects.get(slug='231'),
            'orphan': TestSection.objects.get(slug='1'),
            'rootsection': TestSection.objects.get(slug='2'),
        })

        result = template.render(context)
        self.assertTrue('Passes Test 1' in result)
        self.assertTrue('Passes Test 2' in result)

        # Render with a bad context:
        context = Context({
            'subsection': None,
            'orphan': None,
            'rootsection': None,
        })
        result = template.render(context)
        self.assertTrue('Passes Test 1' not in result)
        self.assertTrue('Passes Test 2' in result)