from pennyblack.models import Newsletter, NewsletterReceiverMixin, Mail
from pennyblack.content.models import RichTextContent
from django.db import models
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
        def add_link(self, link):
            return 'http://replaced.link'

    def setUp(self):
        self.job = self.Job()
        self.content = RichTextContent(text='<a href="http://www.test.com">link</a>')
        
    
    def test_replace_links(self):
        self.content.replace_links(self.job)
        self.assertEqual(self.content.text,'<a href="http://replaced.link">link</a>')

    def test_replace_multiple_links(self):
        self.content.text='<a href="http://www.testmultiple.com">link</a><a href="http://www.2ndlink.com">2ndlink</a>'
        self.content.replace_links(self.job)
        self.assertEqual(self.content.text,'<a href="http://replaced.link">link</a><a href="http://replaced.link">2ndlink</a>')
