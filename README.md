# docker-alias
Enables you to use docker-containers to execute commands as if they are installed on your system.

### Features:
- injectable user-switcher (No more permission problems! Adds a user with the same id as the executing user or modifies a present user and moves it ids)
- variables to allow some dynamic
- auto-image-rebuild
- a docker-compose like configuration

### Requirements:
- docker
- systemd
- lebokus/bindfs:latest (optional)

### Installation
`wget -q -O - "https://gitlab.com/clecherbauer/tools/docker-alias/-/raw/v2.2.11/linux/online-installer.sh" | bash`

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

### YAML Configuration
#### Volumes
like docker-compose 

#### containers
`
auto_rebuild_images: bool | default true
`

images dont get rebuild if content of Directory with Dockerfile changes when set to false

---
`
build: Build | optional
`
like docker-compose 

---
`
commands: List[Command] | optional
`

a list of commands within the container, if not set the container name is used as the main command

---
`
entrypoint: str | optional
`

the entrypoint

---
`
env_file: str | optional
`

the path to a env file

---
`
environment: List[str] | optional
`

a list of environment variables like in docker-compose 

---
`
image: str | optional
`

like docker-compose 

---
`
keep_volumes: bool | default false
`

volumes dont get removed after execution if set to true

---
`
post_exec_hook_command: str
`

not implemented yet

---
`
pre_exec_hook_command: str
`

not implemented yet

---
`
quiet: bool
`

only stdout and stderr from subcommand

---
`
stay_in_root: bool
`

not implemented yet

---
`
volumes: List[Volume]
`

like docker-compose 

---
`
working_dir: str
`
the working dir

---
`
user: str
`

the executing user

---
`
inject_user_switcher: bool
`

Often the `user` attribute is enough to archive file-changes with the same permissions as the executing user.
But if that doesn't work for you  the `inject_user_switcher` could be a solution.

If set to `true`, docker-alias mounts the user-switcher script as a volume and sets it as the main command.
Keep in mind that `--entrypoint` runs fist if is set.

This can help with some tools which rely on home directories or existing user.

DISCLAIMER: This feature is currently only tested with debian based containers and requires the commands `id` `usermod` `groupmod` `useradd` `userdel` `mkdir` `find` `chown` `runuser` to be present.



If you are on a linux host, take a look at [clecherbauer/docker-volume-bindfs](https://github.com/clecherbauer/docker-volume-bindfs), this is an alternative to switching users.

Just add this volume
```
volumes:
  bindfs:
    driver: lebokus/bindfs:latest
    driver_opts:
      sourcePath: "$YAML_LOCATION_DIR"
      map: "$UID/0:@$UID/@0"
```
and add the volume to your container
```
containers:
  somecontainer:
    volumes:
      - bindfs:$DEFAULT_WORKING_DIR
```

---
`
networks: List[str]
`

networks to attach. If a docker-compose default network is present it also gets attached.

---

`
ports: List[str]
`

ports to bind. https://docs.docker.com/config/containers/container-networking/

---

## VARIABLES

Following variables can be set in docker-alias.yml:

- **`$YAML_LOCATION_DIR`**: the path to the nearest directory containing a docker-alias.yml

- **`$DEFAULT_WORKING_DIR`**: /app

- **`$UID`**: the id of the user executing docker-alias
