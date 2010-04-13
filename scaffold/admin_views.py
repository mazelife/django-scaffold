@site.admin_view
@permission_required('sections.can_view_associated_content')
def index(request):
    """
    Admin view: Display a tree of section and subsection nodes.
    Because of the impossibility of expressing needed concepts (like recursion) 
    within the django template syntax, the tree html (nested <ul> elements) is
    constructed manually in this view using the get_rendered_tree and crawl
    functions.
    """
    roots = Section.get_root_nodes()
    node_list_html = '<ul id="node-list" class="treeview-red">'
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
        template = "sections/admin/index.html",
        extra_context = {'node_list':node_list_html, 'title': "Edit Sections"}
    )

    def get_rendered_tree(root_nodes, admin_links=[], html_class=None):
        html_class = html_class and 'class="%s"' % html_class or ""
        tree_html = "<ul%s>%s</ul>" % (
            html_class,
            "".join(map(crawl, root_nodes))        
        )
        return tree_html

    def crawl(node, admin_links=[]):
        link_html = {
            'add_link': (
                "<a class=\"addlink\" href=\"add-to/%s/\">"
                "add child</a>"
            ) % node.pk,
            'del_link': (
                "<a class=\"deletelink\" href=\"delete/%s/\">"
                "delete</a>" 
            )% node.pk,
            'list_link': (
                "<a class=\"changelink\" href=\"related/%s/\">"
                "list content</a>" 
            )% node.pk,
            'order_link': (
                "<a class=\"changelink\" href=\"order/%s/\">"
                "order content</a>"
            ) % node.pk         
        }
        link_list =  " " + " | ".join([link_html[l] for l in admin_links])
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