FROM python:3.7-buster

COPY . /tapiriik

WORKDIR /tapiriik

RUN pip3 install -r requirements.txt

RUN apt-get update && apt-get install -y --no-install-recommends \
	netcat gettext \
	&& rm -rf /var/lib/apt/lists/*


EXPOSE 8000

CMD python3 manage.py runserver 0.0.0.0:8000



# RUN python3 manage.py collectstatic --noinput

# RUN apt-get update && apt-get install -y supervisor
# RUN mkdir -p /var/log/supervisor
# COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# RUN chown -R www-data:www-data /tapiriik


# RUN pip3 install uwsgi 
# ENV UWSGI_WSGI_FILE=tapiriik/wsgi.py
# ENV UWSGI_HTTP=:8000 UWSGI_MASTER=1 UWSGI_HTTP_AUTO_CHUNKED=1 UWSGI_HTTP_KEEPALIVE=1 UWSGI_UID=www-data UWSGI_GID=www-data UWSGI_LAZY_APPS=1 UWSGI_WSGI_ENV_BEHAVIOR=holy
# # # Number of uWSGI workers and threads per worker (customize as needed):
# ENV UWSGI_WORKERS=2 UWSGI_THREADS=4
# # # uWSGI static file serving configuration (customize or comment out if not needed):
# ENV UWSGI_STATIC_MAP="/static/=/tapiriik/static/" UWSGI_STATIC_EXPIRES_URI="/static/.*\.[a-f0-9]{12,}\.(css|js|png|jpg|jpeg|gif|ico|woff|ttf|otf|svg|scss|map|txt) 315360000"

# CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

