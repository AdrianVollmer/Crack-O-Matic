Debian Stable (Buster)
======================

Packages on Pypi are not reviewed, so we will pull the dependencies from the
Debian "Buster" repositories. Doing it this way should reduce the risk of
supply chain attacks, as you only have to trust the Debian maintainers,
which you do already, not all the maintainers of these Pypi packages and
their dependencies.

Also, we will create a dedicated system account named ``crackomatic``. If
you plan to use Crack-O-Matic only in server-less mode, you can use any
regular account instead.

These commands will install the dependencies from the Debian "Buster"
repositories so you don't have to trust packages on Pypi. Only Crack-O-Matic
is pulled from Pypi.

.. code-block:: bash

    # Install python dependencies
    sudo apt install python3-{pip,ldap,ldap3,flaskext.wtf,flask,flask-login,flask-migrate,gevent,sqlalchemy,matplotlib,wtforms,ldap,ldap3,babel,toml,packaging,argon2}

    # Install samba
    sudo apt install samba

    # Create a dedicated system user
    sudo adduser --system crackomatic

    # Install Crack-O-Matic with no Pypi dependencies
    sudo -u crackomatic python3 -m pip install --user --no-deps Crack-O-Matic

    # Add path to $PATH
    sudo -u crackomatic sh -c "echo 'PATH=\$PATH:\$HOME/.local/bin' >> /home/crackomatic/.bashrc"


If you want to use Crack-O-Matic in server-mode, obtain an X.509 certificate
for this system in PEM format. If you don't provide one, Crack-O-Matic will
generate a self-signed certificate with the value of the ``local_address``
argument as its SAN, but that is bad practice and you should get a proper
certificate ASAP.

Put it somewhere safe, like so:

.. code-block:: bash

   sudo mkdir /etc/crackomatic
   sudo mv /path/to/cert.pem /etc/crackomatic/
   sudo mv /path/to/key.pem /etc/crackomatic/
   sudo chown crackomatic /etc/crackomatic/key.pem
   sudo -u crackomatic chmod 600 /etc/crackomatic/key.pem

Fill in the config:

.. code-block:: ini

   # Content of /etc/crackomatic/crackomatic.conf
   local_address = "10.1.0.17"
   port = 3000
   key = "/etc/crackomatic/key.pem"
   cert = "/etc/crackomatic/cert.pem"

Create a systemd daemon:

.. code-block:: ini

   # Content of /etc/systemd/system/crackomatic.service
   [Unit]
   Description=Crack-O-Matic
   After=network.target

   [Service]
   Type=simple
   Restart=always
   ExecStart=/home/crackomatic/.local/bin/crackomatic web
   User=crackomatic

   [Install]
   WantedBy=multi-user.target

Now enable it and run it:

.. code-block:: bash

   sudo systemctl daemon-reload
   sudo systemctl enable crackomatic.service
   sudo systemctl start crackomatic.service

You should be able to access it now at ``https://<local_address>:<port>/``.

Note that you also need to either install John or Hashcat (instructions
below).

Now proceed with the :ref:`preparation`.


Installing John
---------------

The John directory in which the binary lives must be writeable by our
service user. This is somewhat unusual, so I suggest installing it in its
home directory like this:

.. code-block:: bash

   # Install build dependencies
   sudo apt install libssl-dev git
   # Change to crackomatic user and download git repo to home directory
   sudo -u crackomatic -s
   git clone https://github.com/openwall/john.git /home/crackomatic/john
   cd /home/crackomatic/john/src
   ./configure && make -s clean && make -sj4

Read the John documentation if you plan to use GPU support.


Installing Hashcat
------------------

.. code-block:: bash

   sudo apt install hashcat
