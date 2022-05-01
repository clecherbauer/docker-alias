# docker-alias
Enables you to use docker-containers to execute commands as if they where installed on your system.

### Requirements:
- docker
- systemd
- lebokus/bindfs:latest (optional)

### Installation
`wget -q -O - "https://gitlab.com/clecherbauer/tools/docker-alias/-/raw/v2.0.4/linux/online-installer.sh" | bash`

### Usage
1. start docker-alias-daemon with `docker-alias-daemon start`
2. create a new docker-alias.yml and define your volumes and containers / commands:
```
volumes:
  bindfs:
    driver: lebokus/bindfs:latest
    driver_opts:
      sourcePath: "$YAML_LOCATION_DIR"
      map: "$UID/0:@$UID/@0"

containers:
  node:
    image: node
    volumes:
      - bindfs:$DEFAULT_WORKING_DIR
      - $SSH_AUTH_SOCK:/ssh-auth.sock
    commands:
      - node
      - npm
    env_file: .env
    environment:
      - SSH_AUTH_SOCK=/ssh-auth.sock
```
3. register your new docker-alias.yml with `docker-alias add`
4. type in `node`
