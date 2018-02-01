# docker-alias

Bash Aliases for docker
This will hook into the cd command and look for a docker-compose.alias.yml.
The services in it get extracted and a bash alias is generated.

Now you can use "containerized"-tools as if they where installed on your host-machine.

It also exports some handy environment variables:
* PROJECT_ROOT_PATH <- the path where the docker-compose.alias.yml is stored
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
<<< docker-compose.alias.yml >>>
version: '3'

services:
  node:
    image: node:4
    volumes:
     - ${PROJECT_ROOT_DIR}:/var/www/html
    working_dir: /var/www/html
    labels:
     - com.docker-alias.name=npm
```

There are 3 labels available:
```
com.docker-alias.name=npm <- the alias name
com.docker-alias.command=/bin/bash <- [Optional] the command wich should be executed in the container, if not set the name will be used as the command
com.docker-alias.service=node <- [Optional] the docker-compose service wich should be used, if not set the service in wich this label appears is used
```

Now cd into the path with the docker-compose.alias.yml and type docker-alias

### Build
```
    make
```