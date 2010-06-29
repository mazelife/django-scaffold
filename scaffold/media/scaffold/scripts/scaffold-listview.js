$(document).ready(function(){
    
    // Show toolbar (only relevant with JS on)
    $('#toolbar').show();
    
    // Create tree
    $("#node-list").jstree({
        'core': {},
        'plugins': ['themes', 'html_data', 'search', 'cookies'],
        'themes': {
            'theme': 'django',
            'icons': false
        },
        'search': {
            'case_insensitive': true
        }
    })
    
    // Annotate search results
    .bind("search.jstree", function (e, data) {
        $('#changelist-search p').remove();
        var l = data.rslt.nodes.length;
        $('<p />', {
            'id': 'search-result',
            'html': l + ' page' + ((l==1) ? '' : 's') + ' matching <strong>&ldquo;' + data.args[0] + '&rdquo;</strong> [<abbr title="Clear Search">x</abbr>]'
        }).appendTo('#changelist-search')
    });
    
    // Do the search thing
    $("#changelist-search").bind('submit', function(evt){
        evt.preventDefault();
        $("#node-list").jstree('search', $(this).find('input[type="text"]').val());
    });
    
    // Clearing the search
    $('#changelist-search p abbr').live('click', function(){
        $("#node-list").jstree('clear_search');
        $("#changelist-search")
            .find('input[type="text"]')
                .val('')
                .focus()
            .end()
            .find('p')
                .remove();
    });
    
    // Highlight row on hover (and on link list hover)
    $('.jstree li > span').mouseover(function(){
        $(this).addClass('hover');
    }).mouseout(function(){
        $(this).removeClass('hover');
    });
    $('.jstree li > .links').mouseover(function(){
        $(this).siblings('span').addClass('hover');
    }).mouseout(function(){
        $(this).siblings('span').removeClass('hover');
    });
    
});