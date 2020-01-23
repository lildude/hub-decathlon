FROM python:3

COPY . /tapiriik

WORKDIR /tapiriik

RUN pip3 install -r requirements.txt

RUN apt-get update && apt-get install -y --no-install-recommends \
	netcat gettext \
	&& rm -rf /var/lib/apt/lists/*

#ADD local_settings.py tapiriik/local_settings.py

CMD python3 manage.py runserver 0.0.0.0:8000
