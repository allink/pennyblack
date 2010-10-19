from pennyblack.models import Newsletter, NewsletterReceiverMixin, NewsletterMail
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

# class NewsletterMailTest(unittest.TestCase):
#     receiver = None
#     mail = None
#     def setUp(self):
#         receiver = NewsletterReceiver()
#         mail = NewsletterMail(person=self.receiver)
#     
#     def test_is_valid(self):
#         self.assertFalse(self.mail.is_valid())
        