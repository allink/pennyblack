from django import template

register = template.Library()

class NewsletterstyleNode(template.Node):
    def __init__(self, key, style, request):
        self.key = key
        self.style = style
        self.request_var = template.Variable(request)
        
    def render(self, context):
        request = self.request_var.resolve(context)
        if not hasattr(request, '_pennyblack_newsletterstyle'):
            setattr(request, '_pennyblack_newsletterstyle', dict())
        request._pennyblack_newsletterstyle[str(self.key)] = self.style.render(context)
        return ''

def newsletterstyle(parser, token):
    """
    Stores the content in your context
    {% newsletterstyle request text_only_content %}
    """
    bits = list(token.split_contents())
    if len(bits) != 3 :
        raise template.TemplateSyntaxError("%r expected format is 'newsletterstyle request stylename'" %
            bits[0])
    request = bits[1]
    key = parser.compile_filter(bits[2])
    style = parser.parse(('endnewsletterstyle',))
    parser.delete_first_token()
    print style
    return NewsletterstyleNode(key, style, request)
newsletterstyle = register.tag(newsletterstyle)

class NewsletterGetStyleNode(template.Node):
    def __init__(self, key, request):
        self.key = key
        self.request_var = template.Variable(request)
    
    def render(self, context):
        request = self.request_var.resolve(context)
        if not hasattr(request, '_pennyblack_newsletterstyle'):
            return ''
        if str(self.key) not in request._pennyblack_newsletterstyle.keys():
            return ''
        return request._pennyblack_newsletterstyle[str(self.key)]
        
def get_newsletterstyle(parser, token):
    """
    Loads a stored style and renders it
    """
    bits = list(token.split_contents())
    if len(bits) != 3 :
        raise template.TemplateSyntaxError("%r expected format is 'newsletterstyle request stylename'" %
            bits[0])
    request = bits[1]
    key = parser.compile_filter(bits[2])
    return NewsletterGetStyleNode(key, request)
get_newsletterstyle = register.tag(get_newsletterstyle)
    