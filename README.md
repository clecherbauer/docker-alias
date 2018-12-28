# docker-alias

Bash Aliases for docker
This will hook into the cd command and look for a docker-alias.yml.
The services in it get extracted and a bash alias is generated.

Now you can use "containerized"-tools as if they where installed on your host-machine.

It also exports some handy environment variables:
* PROJECT_ROOT_PATH <- the path where the docker-alias.yml is stored
* LOCAL_UID <- the executers uid
* LOCAL_GID <- the executers gid

### Installing

Clone this repo onto your desired destination and source the auto-docker-alias file in your .bashrc or .zshrc:

```
source /path/to/repo/auto-docker-alias.sh
PATH=$PATH:/path/to/repo
```

### Usage

Create a docker-compose.alias.yml file and define your services:
```
<<< docker-alias.yml >>>
version: '3'

services:
  node:
    image: node:4
    volumes:
     - ${PROJECT_ROOT_DIR}:/app
    working_dir: /app
    labels:
     - com.docker-alias.name=npm
```

There are following labels available:

`com.docker-alias.name=npm` - the alias name and command

`com.docker-alias.command=/bin/bash` - [Optional] the command wich should be executed in the service, if empty the name will be used as the command

`com.docker-alias.service=node` - [Optional] the service wich should be used, if not set the service in wich this label appears is used

`com.docker-alias.user=www-data` - [Optional] the user wich should be used to execute the service

`com.docker-alias.keepRoot=true` - [Optional] the command is executed in the services defined workdirectory


Now cd into the path with the docker-alias.yml and type docker-alias

### Tips and Tricks

Avoid file-permission problems with the [lebokus/bindfs](https://github.com/lebokus/docker-volume-bindfs) docker plugin.
```
<<< docker-alias.yml >>>
version : '3'

volumes:
  alias_bindfs_mapped_data:
    driver: lebokus/bindfs:latest
    labels:
     - com.docker-alias=true
    driver_opts:
      sourcePath: "${PROJECT_ROOT_PATH}"
      map: "${LOCAL_UID}/0:@${LOCAL_UID}/@0"

services:
  node:
    image: node:4
    volumes:
     - alias_bindfs_mapped_data:/app
    working_dir: /app
    labels:
      - com.docker-alias.name=node
```