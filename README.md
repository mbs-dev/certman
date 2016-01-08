Certificates Storage Manager
===

1. Install ```sudo pip install git+https://github.com/mbs-dev/certman.git```
2. Run configuration ```certman-config``` and enter path to the SQLite database, directory to store raw data and default password for certs.
3. Run ```certman``` to manage certs.

Development
===
1. Checkout repository ```git clone git@github.com:mbs-dev/certman.git``` and open it ```cd certman```
2. Build virtualenv ```virtualenv env``` and activate it ```source env/bin/activate```
3. Install it for development: ```python setup.py develop```
4. Or just run tests: ```python setup.py test```

After installing for development you will be able to change source code and
immediately see updates, while running `certman` under `virtualenv`.
