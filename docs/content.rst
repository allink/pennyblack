Content Types
=============

Compared with FeinCMS content types, pennyblack content types can provide further functionality

Additional hooks
****************

- replace_links
    This method if it exists is called before the newsletter is sent. It should replace all links with a newly generated link to be able to track every link click:
    ::
    
        HREF_RE = re.compile(r'href\="((\{\{[^}]+\}\}|[^"><])+)"')
        
        def replace_links(self, job):
            """
            Replaces all links and inserts pingback links
            """
            offset = 0
            for match in HREF_RE.finditer(self.text):
                link = match.group(1)
                if check_if_redirect_url(link):
                    continue
                # don't replace links to proxy view
                if u'link_url' in link:
                    continue
                replacelink = job.add_link(link)
                self.text = ''.join((self.text[:match.start(1)+offset], replacelink, self.text[match.end(1)+offset:]))
                offset += len(replacelink) - len(match.group(1))
        
 
- prepare_to_send
    Is meant to add some additional style informations into the content. Because email clients often only accept inline style information.
    ::
    
        def prepare_to_send(self):
            """
            insert link_style into all a tags
            """
            self.text = re.sub(r"<a ","<a {% get_newsletterstyle request text_and_image_title %}", self.text)


Provided content types
======================
Pennyblack comes with some content types bundled which sould be sufficient for most use cases.

.. currentmodule:: pennyblack.content.richtext
.. autoclass:: TextOnlyNewsletterContent

.. autoclass:: TextWithImageNewsletterContent

