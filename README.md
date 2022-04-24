# docker-alias

Enables you to use docker-containers to execute commands as if they where installed on your system.

### Requirements:
- docker
- systemd
- lebokus/bindfs:latest (optional)

### Installation

`wget -q -O - "https://raw.githubusercontent.com/clecherbauer/docker-alias/2.0.0/online-installer.sh" | bash`

### Usage

1. create a new docker-alias.yml and define your volumes and commands:

```
volumes:
  bindfs:
    driver: lebokus/bindfs:latest
    driver_opts:
      sourcePath: "$YAML_LOCATION_DIR"
      map: "$UID/0:@$UID/@0"

containers:
  python:
    build:
      context: .
      dockerfile: .devops/docker/alias/python/Dockerfile
    volumes:
      - bindfs:$DEFAULT_WORKING_DIR
      - $SSH_AUTH_SOCK:/ssh-auth.sock
    commands:
      - python
      - pip3:
          path: /usr/local/bin/pip3
      - flake8
      - autopep8
      - prospector
      - prospector-html
    env_file: .env
    environment:
      - PYTHONPATH=$DEFAULT_WORKING_DIR
    entrypoint: /usr/local/bin/entrypoint.sh

  node:
    image: node
    volumes:
      - bindfs:$DEFAULT_WORKING_DIR
      - $SSH_AUTH_SOCK:/ssh-auth.sock
    commands:
      - node
      - npm
      - npx
      - vue
    env_file: .env
    environment:
      - SSH_AUTH_SOCK=/ssh-auth.sock
```

2. register your new docker-alias.yml with `docker-alias add`

3. try out your commands

