PYPREFIX_PATH=/usr
PYTHONLIBS=LD_LIBRARY_PATH=/usr/lib
PYTHONPATH=$(PYPREFIX_PATH)/bin/python
FIRST_EASYINSTALL=$(PYTHONLIBS) easy_install
PIP=pip
PYTHON=bin/python
EASYINSTALL=bin/easy_install
VIRTUALENV=virtualenv
SOURCE_ACTIVATE=$(PYTHONLIBS) . bin/activate; 

unattended:
	@ (sudo ls 2>&1) >> tracking.log

$(LIBSQLITE3):
	$(call install,sqlite-autoconf-3080701,sqlite-autoconf-3080701.tar.gz,http://www.sqlite.org/2014)

bin/activate: imagedownloader/requirements.txt
	@ echo "[ using        ] $(PYTHONPATH)"
	@ echo "[ installing   ] $(VIRTUALENV)"
	@ (sudo $(FIRST_EASYINSTALL) virtualenv 2>&1) >> tracking.log
	@ echo "[ creating     ] $(VIRTUALENV) with no site packages"
	@ ($(PYTHONLIBS) $(VIRTUALENV) --python=$(PYTHONPATH) --no-site-packages . 2>&1) >> tracking.log
	@ echo "[ installing   ] $(PIP) inside $(VIRTUALENV)"
	@ ($(SOURCE_ACTIVATE) $(EASYINSTALL) pip 2>&1) >> tracking.log
	@ echo "[ installing   ] $(PIP) requirements"
	@ $(SOURCE_ACTIVATE) $(PIP) install -e  .
	@ $(SOURCE_ACTIVATE) $(PIP) install --default-timeout=100 -r requirements.development.txt 2>&1 | grep Downloading
	@ touch bin/activate

bash-config:
	@ echo "[ configure    ] change the limit to allowed open files by user"
	@ echo "ulimit -n 10240" >> ~/.bashrc

deploy: bin/activate bash-config
	@ echo "[ deployed     ] the system was completly deployed"

show-version:
	@ $(SOURCE_ACTIVATE) $(PYTHON) --version

test: bash-config
	@ $(SOURCE_ACTIVATE) $(PYTHON) tests/__main__.py

test-coverage-travis-ci: bash-config
	@ $(SOURCE_ACTIVATE) && coverage run --source='requester/models/' manage.py test requester

test-coveralls:
	@ $(SOURCE_ACTIVATE) cd imagedownloader && coveralls

test-coverage: test-coverage-travis-ci test-coveralls

shell: bash-config
	@ $(SOURCE_ACTIVATE) cd imagedownloader && ../$(PYTHON) manage.py shell	

clean:
	@ echo "[ cleaning     ] remove deployment generated files that doesn't exists in the git repository"
	@ sudo rm -rf sqlite* python-aspects* virtualenv* bin/ lib/ lib64 include/ build/ share Python-* .Python get-pip.py tracking.log imagedownloader/imagedownloader.sqlite3 subversion
