Bouncedetection
***************
Pennyblack comes with automatic bounce detection. Use the following explanation
to get bounce detection up and running:

Configuration
-------------
the following in your settings file::

    PENNYBLACK_BOUNCE_DETECTION_ENABLE = True

Mailman installation
--------------------
To automatically detect bounces pennyblack uses a patched mailman installation
which allows it to pass a email as text and receive a coma separated list of
email addresses which have bounced. This is because mailman is published under
gpl which only allows direct inclusion if only simple datatypes are exchanged.

*   Download a copy of mailman 2.x from http://www.list.org/download.html and
    unpack it into a directory which is on your python path.
*   Use the mailman_patch included in the gitrepository of pennyblack::

        cd Mailman
        patch -p1 -i path_to/mailman_patch.patch

Sender configuration
--------------------
Fill in imap credentials in for the sender in the admin and check
``Get bounce e-mails``.

Cronjob
-------
Set up a cronjob to execute ``./manage.py getmail`` regularly.

Where did all the emails go?
============================
Pennyblack moves every email which is recognized as a bounce email into
INBOX.bounced. This folder can be renamed by altering the settings.