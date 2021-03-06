You have two choices: Run Crack-O-Matic in server mode with a Flask-based
web interface which you can access with a browser, or run it in server-less
mode, in case you just want to run a one-off audit on the command line of
the server.

.. _preparation:

Preparation
===========

No matter which mode you choose, there are a few things you must prepare.
Shell access is necessary for the preparation.

#. Keep the root certificate of your Active Directory LDAP service in PEM format ready.

#. If you want to use TLS with the SMTP server, get the corresponding root certificate as well, if it is different than the one from the previous step.

#. Download a suitable wordlist such as `CrackStation <https://crackstation.net/crackstation-wordlist-password-cracking-dictionary.htm>`_ and copy it onto the system.

#. Install either `John "Jumbo" <https://github.com/openwall/john>`_ or `Hashcat <https://hashcat.net/hashcat/>`_. If you choose John, make sure to install the "Jumbo" version. You might have to compile it yourself, as many distributions do not ship the Jumbo version. Kali Linux is one that does.  Hashcat is more readily available. Note that Hashcat can take advantage of graphics cards if the right drivers are installed. Please refer to the respective documentation for installation. You also may want to download a ruleset for Hashcat such as `OneRule <https://notsosecure.com/one-rule-to-rule-them-all/>`_.

#. Create a dedicated account and put it in the group of domain administrators. Give it a strong password!

Server Mode
===========

This mode is recommended if you want automated, regularly scheduled audits
with graphical reports or you have several people working with Crack-O-Matic.


First access
------------

First, create a local account by executing ``crackomatic user --add
<username>`` on the command line. You can setup simple LDAP authentication
later so you can authenticate with your Active Directory account. All
accounts are equal. No matter if local or not, there is only one account
role.

Now you are ready to launch Crack-O-Matic with ``crackomatic web``.


Configuration
-------------

Authentication
~~~~~~~~~~~~~~

After you log on with a local account, you can head to the "Config" section
and set up `simple LDAP authentication
<https://ldapwiki.com/wiki/Simple%20Authentication>`_. This is optional.

If you want to able to login with an Active Directory account, you need to
fill out the LDAP URL of a domain controller (use the FQDN), the local path
to the corresponding root CA in PEM format, the bind DN (what the user
object's distinguished name looks like), the search base DN (where to look
in the directory) and an LDAP filter (who is authorized to log on). An
example could be:

.. code-block::

    LDAP URL = ldaps://dc1.contoso.local:636
    CA File = /home/crackomatic/contoso-ca.pem
    Bind DN = CN=%s,CN=Users,DC=contoso,DC=local
    Base DN = CN=Users,DC=contoso,DC=local
    LDAP Filter = (&(objectClass=user)(memberOf=CN=crackomatic_admins,OU=users,DC=contoso,DC=local))

In the bind DN, ``%s`` will be replaced with the login ID of the user trying
to authenticate in the web application.


Cracker
~~~~~~~

For the cracker, you must choose between John and Hashcat.

Crack-O-Matic does not come with a wordlist. You need to download a wordlist
and specify a local path to that file in the "Cracker" section.
`CrackStation
<https://crackstation.net/crackstation-wordlist-password-cracking-dictionary.htm>`_
offers a large wordlist that is suitable.

You should also specify cracking rules. A very sensible rule set for this
purpose is `OneRule <https://notsosecure.com/one-rule-to-rule-them-all/>`_
in case you chose Hashcat. Specify the path to the rule file in the settings.

For John, ``dive`` is a rather large rule set you can use. It comes with
John Jumbo. Specify only the name, not the path to the rule file.

Depending on your hardware, you may want to choose a smaller wordlist or a
smaller rule set if one audit does not finish within a week or so. However,
computing NT hashes is cheap and they are unsalted, so we can usually afford
the largest wordlists and rule sets there are.

E-Mail
~~~~~~

This is required so the results can be sent out via e-mail. The fields
should be self explanatory. If you use TLS, keep the CA in PEM format ready.


Audits
------

In the "Audits" section, you can create and manage your audits. They can be
run just once or on a regular basis. Fill out all the fields to run or
schedule an audit.

.. warning::
    Note the security considerations in the section below.

To check if you set everything up properly, try running an audit "just once"
and "right now". You can later "clone" the audit and carry over most
settings.

If you run into the problem of some users becoming frustrated because their
passwords are cracked in every iteration, you are free to exclude them from
the notification mails by adjusting the LDAP filter. For this, you could
create an inclusive or an exclusive group of users. However, I recommend
auditing the passwords of all accounts who have administrative permissions
on at least one domain-joined system. With great power comes great
responsibility and they should know better than to choose weak passwords.


Server-less Mode
================

This mode is recommended if you want to manually run Crack-O-Matic once in a
while. This is useful if you want to shut down the machine in between
audits or you want to decrease the attack surface of the application.
It could also be used as part of a cron job.

Instructions
------------

Execute ``crackomatic audit -s`` to generate an empty audit file. You now
need to fill in these fields. Execute ``crackomatic audit -d`` for a
description of each field. You can leave certain fields such as the password
field empty and specify the ``--interactive`` switch, in which case you will
prompted for missing fields. Here is an example of an audit file:

.. code-block:: json

    {
        "audit": {
            "admin_filter": "(&(objectClass=user)(memberOf=cn=crackomaticAdmins,OU=Users,DC=contoso,DC=local))",
            "ca_file": "/home/user/root-ca.pem",
            "dc_ip": "10.10.10.10",
            "domain": "contoso.local",
            "email_field": "mail",
            "include_cracked": "y",
            "ldap_uri": "ldaps://dc01.contoso.local:636",
            "message": "Dear User,\n\nyour password has been identified as too weak.\n\n...",
            "password": "",
            "subject": "Regarding your password",
            "user": "svc_crackomatic",
            "user_filter": "(objectClass=person)"
        },
        "cracker": {
            "binary_path": "/usr/bin/hashcat",
            "cracker": "Hashcat",
            "rule_path": "/opt/rules/OneRuleToRuleThemAll.rule",
            "wordlist_path": "/opt/wordlists/crackstation.txt"
        },
        "email": {
            "smtphost": "exch01.contoso.local",
            "smtppass": "",
            "smtpport": "25",
            "smtpsender": "noreply@admin.contoso.local",
            "smtptls": "",
            "smtpuser": "svc_mail"
        }
    }

Note that for boolean fields such as ``smtptls`` or ``include_cracked`` that
empty means ``False`` and everything else means ``True``. See the previous
section for more details.

When you are finished, execute ``crackomatic audit <path to audit file>`` to
run the audit. If you want to do a test run, choose a short wordlist and see
if the results make sense. Next, you may want to set the ``user_filter``
attribute to just yourself: ``(sAMAccountName=johndoe)``


Security
========

The account which Crack-O-Matic is using to access your users' passwords
obviously has powerful permissions. Protect it as well as a domain
administrator account. In the words of Microsoft's `Enterprise access model
<https://docs.microsoft.com/en-us/security/compass/privileged-access-access-model>`_,
it belongs to the control plane. This model was formerly known as the
administrative tier model, in which the control plane was called tier 0.

Similarly, the system Crack-O-Matic is running on is as powerful as a domain
controller. It, too, belongs in tier 0.

Do not use the Crack-O-Matic service account for anything else. Choose a
strong and unique password. Put this account into the group of domain
administrators.

If you want to harden the system even more, you could block all incoming
connections except for SSH and HTTP and all outgoing connections except the
ones needed for receiving OS updates, all connections to at least one domain
controller as well as the SMTP port of the e-mail server. In particular,
internet access should not be allowed, unless it goes to the update servers.
Incoming connections could further be restricted to workstations of
authorized personnel.
