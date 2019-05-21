# Thing's you'll need
* A computer (*nix preferred, but I've gotten it working on Windows too)
* libxslt-dev + libxml2-dev **OR** a working install of the Python `lxml` package
* MongoDB >=2.6
* Redis
* RabbitMQ
* Python >=3.3 (with pip, of course)

# Setup
1. Clone the repository to a directory of your choice (due to an unfortunate dependency that I should fix, the tarball won't work)
2. *(optional, but recommended)* Create a virtualenv (e.g. `virtualenv tap-env`) and activate it (e.g. `source tap-env/bin/activate`) so we can keep our packages under control
3. Install the requirements via pip - `pip install -r requirements.txt`
4. Copy local_settings.py `cp tapiriik/local_settings.py.example tapiriik/local_settings.py`
5. Run `python credentialstore_keygen.py` and paste the output into your local_settings.py file (`python credentialstore_keygen.py >> tapiriik/local_settings.py`)

## Ubuntu 14.04

Copy and paste :smile: 

* `sudo apt-get install git python3-pip mongodb redis-server rabbitmq-server libxslt-dev libxml2-dev python3-lxml python3-crypto`
* `git clone https://github.com/cpfair/tapiriik.git`
* `cd tapiriik`
* `sudo pip3 install -r requirements.txt`
* `cp tapiriik/local_settings.py.example tapiriik/local_settings.py`
* `python3 credentialstore_keygen.py >> tapiriik/local_settings.py`
* `python3 manage.py runserver 0.0.0.0:8000`

# Startup
1. Start `mongod` and `redis-server` and `rabbitmq-server`
2. Run `python manage.py runserver` to start the web interface (run `python manage.py runserver 0.0.0.0:8000` to listen on all interfaces) - you should now be able to navigate to [localhost:8000](http://localhost:8000) and marvel at your very own copy of tapiriik.com
3. Run `python ./sync_worker.py` to start a synchronization worker, and `python ./sync_scheduler.py` to start the scheduler (otherwise you'll only ever see "Queueing to Synchronize," and we know how fun *that* is)

# [Back to summary](000-summary.md)
## [Back to install summary](001-install.md)
