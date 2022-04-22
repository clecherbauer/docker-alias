FROM registry.gitlab.com/clecherbauer/docker-images/python:3.8-debian-bullseye

WORKDIR /var/source
COPY . /var/source
RUN /var/source/.devops/docker/alias/python/build.sh

WORKDIR /app
CMD ["/usr/local/bin/entrypoint.sh"]
