Ethical and legal considerations
================================

Let it be known that I am not a lawyer, and laws depend on your location
anyway. However, you may want to check with your legal department, human
resources and/or union representative if you want to use Crack-O-Matic.
Passwords are a very personal and very sensitive piece of
information. Users might protest against regular password audits, as some of
them might be reusing their passwords in other services and feel
uncomfortable at the thought that somebody may see their passwords.

This is why you will never see a password or even a password hash in the web
interface of Crack-O-Matic.

Even the account names won't be visible to you by default. Only the affected
users will know that their password has been identified as weak. Of
course, somebody with the appropriate access to the mail server's logs will
be able to tell, but this will most likely be a trusted person that already
has special privileges anyway.

Can I trust this program?
=========================

Crack-O-Matic is free and open source, does not require registration and
respects your privacy. Feel free to review `the source code
<https://github.com/AdrianVollmer/Crack-O-Matic>`_ and its dependencies,
which all have sufficient reputation to be in the Debian repositories.

Limitations
===========

Obviously, Crack-O-Matic can only check passwords of domain accounts. There
may be systems which may be critical to your business operations but are not
joined to a domain, so their accounts are not subject to your password
policy. This could be appliances, Linux systems, firewalls, and so on. Don't
forget to pay special attention to these systems.

The same goes for local Windows accounts. These are not visible to
Crack-O-Matic. You should use `LAPS
<https://www.microsoft.com/en-us/download/details.aspx?id=46899>`_ to manage
those if you don't already.
