FROM registry.gitlab.com/clecherbauer/docker-images/node-nginx:14-buster

WORKDIR /var/source
COPY . /var/source
RUN /var/source/.devops/docker/alias/node/build.sh

WORKDIR /app