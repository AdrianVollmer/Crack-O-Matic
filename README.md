Crack-O-Matic
=============

Find and notify users in your Active Directory with weak passwords.

Features:

* Linux-based
* Flask-based web app
* Hashcat or John cracker
* Automated e-mails
* Graphical reports
* Privacy preserving

[Read the docs](https://crack-o-matic.readthedocs.io) for more information.


Screenshots
-----------

![Report 1](https://github.com/AdrianVollmer/Crack-O-Matic/blob/main/doc/report1.png)

![Report 2](https://github.com/AdrianVollmer/Crack-O-Matic/blob/main/doc/report2.png)


Tests
-----

If you're a developer and want to run the tests, you need to edit
`tests/.env` and define the following variables according to your
environment:

```
# path to `john` binary
JOHN_PATH=/opt/john/run/john
# path to `hashcat` binary
HASHCAT_PATH=/usr/bin/hashcat
# FQDN of a test domain
DOMAIN=crack.local
# name of one of its domain admins
DOMAINUSER=Administrator
# domain admin password
DOMAINPASS=
# FQDN of a domain controller in the test domain
HOST=localdc.crack.local
```

If you don't have a test domain, you can use the docker-compose file in
`tests/docker` to run a Samba DC (`docker-compose run --service-ports dc`).
Inside the file you will find the values you need. You should also create an
entry for the FQDN in your `/etc/hosts`.

License and Copyright
---------------------

MIT, Copyright 2021 Adrian Vollmer

See LICENSE for the full license text.
