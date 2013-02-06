# coding=utf-8
from pennyblack.models.newsletter import Newsletter
from pennyblack.models.job import Job, JobStatistic
from pennyblack.models.link import Link, LinkClick
from pennyblack.models.mail import Mail
from pennyblack.models.sender import Sender
from pennyblack.models.emailclient import EmailClient

__all__ = ('Newsletter', 'Job', 'JobStatistic', 'Link', 'LinkClick', 'Mail', 'Sender', 'EmailClient')
