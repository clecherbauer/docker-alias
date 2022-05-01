# docker-alias
Enables you to use docker-containers to execute commands as if they are installed on your system.

### Requirements:
- docker
- systemd
- lebokus/bindfs:latest (optional)

### Installation
`wget -q -O - "https://gitlab.com/clecherbauer/tools/docker-alias/-/raw/v2.1.0/linux/online-installer.sh" | bash`

### Usage
1. start docker-alias-daemon with `docker-alias-daemon start`
2. create a new docker-alias.yml and define your volumes and containers / commands.
For example:
```
containers:
  node:
    image: node
    volumes:
      - $YAML_LOCATION_DIR:$DEFAULT_WORKING_DIR
      - $SSH_AUTH_SOCK:/ssh-auth.sock
    commands:
      - node
      - npm
    env_file: .env
    environment:
      - SSH_AUTH_SOCK=/ssh-auth.sock
    user: $UID
```
3. register your new docker-alias.yml with `docker-alias add`
4. type in `node`


## VARIABLES

Following variables can be set in docker-alias.yml:

- **`$YAML_LOCATION_DIR`**: the path to the nearest directory containing a docker-alias.yml

- **`$DEFAULT_WORKING_DIR`**: /app

- **`$UID`**: the id of the user executing docker-alias
