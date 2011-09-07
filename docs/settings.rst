Settings
========

.. currentmodule:: pennyblack.default_settings

General Settings
----------------

.. attribute:: TINYMCE_CONFIG_URL

Newsletter
----------

.. attribute:: NEWSLETTER_TYPE

    Defines the available newsletter types. Normally you don't have to change
    these.

.. attribute:: NEWSLETTER_TYPE_MASSMAIL

    A tuple with all NEWSLETTER_TYPE id's which are considered a massmail
    newsletter.
    
    Massmail are newsletters which are sent to many receivers at the same
    time.

.. attribute:: NEWSLETTER_TYPE_WORKFLOW

    A tuple with all NEWSLETTER_TYPE id's wich are considered a workflow
    newsletter.
    
    Workflow newsletters are emails wich are sent to each receiver
    indivitually, for example a registration complete email wich is sent
    right after a user registers.

.. attribute:: NEWSLETTER_CONTENT_WIDTH

    The content with of a newsletter, has to match the with in the template.

.. attribute:: TEXT_AND_IMAGE_CONTENT_POSITIONS

    A list of position choices for the TextWithImageNewsletterContent.

.. attribute:: TEXT_AND_IMAGE_CONTENT_IMAGE_WIDTH_SIDE

.. attribute:: JPEG_QUALITY
    
    The quality in percent which is used to compress jpeg images.

Job
---

.. attribute:: JOB_STATUS

.. attribute:: JOB_STATUS_CAN_SEND

.. attribute:: JOB_STATUS_PENDING

.. attribute:: JOB_STATUS_CAN_EDIT

Bounce detection
----------------

.. attribute:: BOUNCE_DETECTION_ENABLE

.. attribute:: BOUNCE_DETECTION_DAYS_TO_LOOK_BACK

.. attribute:: BOUNCE_DETECTION_BOUNCE_EMAIL_FOLDER

