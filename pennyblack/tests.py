from pennyblack.models import Newsletter, Mail
from pennyblack.options import NewsletterReceiverMixin
from pennyblack.content.richtext import TextOnlyNewsletterContent
from django.db import models
from django.core.urlresolvers import reverse
import unittest

class NewsletterTestCase(unittest.TestCase):
    # def setUp(self):
    #     pass
        
    def test_is_valid(self):
        n = Newsletter()
        self.assertFalse(n.is_valid(), "Empty Newsletter can not be valid.")
        n.subject = 'some text'
        self.assertTrue(n.is_valid(), "Newsletter should be valid now.")

# class MailTest(unittest.TestCase):
#     receiver = None
#     mail = None
#     def setUp(self):
#         receiver = NewsletterReceiver()
#         mail = Mail(person=self.receiver)
#     
#     def test_is_valid(self):
#         self.assertFalse(self.mail.is_valid())

class RichtextContentTest(unittest.TestCase):
    content = None
    job = None
    class Job(object):
        def __init__(self, link):
            self.times = 0
            self.link = link
        def add_link(self, link):
            self.times += 1
            return '{{base_url}}' + self.link

    def setUp(self):
        self.content = TextOnlyNewsletterContent(text='<a href="http://www.test.com">link</a>')
        self.link = reverse('pennyblack.redirect_link', kwargs={'mail_hash':'{{mail.mail_hash}}','link_hash':'1234'}).replace('%7B','{').replace('%7D','}')
        self.job = self.Job(self.link)
        
    
    def test_replace_links(self):
        self.content.replace_links(self.job)
        self.assertEqual(self.content.text,'<a href="{{base_url}}%s">link</a>' % self.link)

    def test_replace_multiple_links(self):
        self.content.text='<a href="http://www.testmultiple.com">link</a><a href="http://www.2ndlink.com">2ndlink</a>'
        self.content.replace_links(self.job)
        self.assertEqual(self.content.text,'<a href="{{base_url}}%s">link</a><a href="{{base_url}}%s">2ndlink</a>' % (self.link, self.link))
    
    def test_dont_replace_twice(self):
        self.content.text = '<a href="http://www.allink.ch">link</a>'
        self.content.replace_links(self.job)
        old_times = self.job.times
        last_text = self.content.text[:]
        self.content.replace_links(self.job)
        self.assertEqual(self.job.times, old_times)
        self.assertEqual(self.content.text, last_text)
    
    def test_dont_replace_link_url_tag_urls(self):
        link = '<a href="{% link_url my_identifier%}">link</a>'
        self.content.text = link
        self.content.replace_links(self.job)
        self.assertEqual(self.content.text,link)
    
    def test_quotes_in_url(self):
        self.content.text = '<a href="http://test{{somevariable|with:"quotes"}}">link</a>'
        self.content.replace_links(self.job)
        self.assertEqual(self.content.text,'<a href="{{base_url}}%s">link</a>' % self.link)
    
    def test_link_style(self):
        self.content.text = '<a >link</a>'
        self.content.prepare_to_send()
        self.assertEqual(self.content.text,'<a {% get_newsletterstyle request text_and_image_title %}>link</a>')

    def test_multiple_link_styles(self):
        self.content.text = '<a >link</a><a >link</a>'
        self.content.prepare_to_send()
        self.assertEqual(self.content.text,'<a {% get_newsletterstyle request text_and_image_title %}>link</a><a {% get_newsletterstyle request text_and_image_title %}>link</a>')
