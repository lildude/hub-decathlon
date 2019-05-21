# Docker
* First of all initiate the file **tapiriik/local_settings.py**
* Then build the docker to get all the requierements.

* If you're running into dev environment and building this docker image for the first time, don't forget to create an empty ```environment``` file

* Finaly launch the docker-compose to get all the containers (redis, mongo, web, RMQ)
```shell
docker build --no-cache -t my-hub-decathlon .
docker-compose up
```
# [Back to summary](000-summary.md)
