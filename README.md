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


Tests
-----

If you're a developer and want to run the tests, you need to edit
`tests/.env` and define the following variables according to your
environment:

* `JOHN_PATH` (path to `john` binary)
* `HASHCAT_PATH` (path to `hashcat` binary)
* `DOMAIN` (FQDN of a test domain)
* `DOMAINUSER` (name of one of its domain admins)
* `DOMAINPASS` (domain admin password)
* `HOST` (FQDN of a domain controller in the test domain)

If you don't have a test domain, you can use the docker-compose file in
`tests/docker` to run a Samba DC (`docker-compose run --service-ports dc`).
Inside the file you will find the values you need. You should also create an
entry for the FQDN in your `/etc/hosts`.

License and Copyright
---------------------

MIT, Copyright 2021 Adrian Vollmer

See LICENSE for the full license text.
