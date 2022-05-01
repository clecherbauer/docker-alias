import argparse
import os.path
import sys

from config import INIConfig, YAML_CONFIG_FILE_NAME, INI_CONFIG_FILE_PATH, VERSION
from docker_util import DockerUtil
from container import ContainerUtil


class DockerAliasCLI(object):
    ini_config = INIConfig()
    add_description = 'Adds a new {yaml_config_file} to {ini_config_file}'.format(
        yaml_config_file=YAML_CONFIG_FILE_NAME,
        ini_config_file=INI_CONFIG_FILE_PATH
    )
    remove_description = 'Removes a {yaml_config_file} from {ini_config_file}'.format(
        yaml_config_file=YAML_CONFIG_FILE_NAME,
        ini_config_file=INI_CONFIG_FILE_PATH
    )
    list_description = 'List all containers and their commands'
    run_description = 'Runs an command in an container'
    build_description = 'Builds container-images'
    usage = '''
docker-alias <command> [<args>]

Available Commands:
   add      {add_description}
   build    {build_description} [ all || <container_name> ]
   list     {list_description}
   remove   {remove_description}
   run      {run_description} [ <container_name> || <command_name> ]

Version: {version}
'''

    quiet = False

    def __init__(self):
        parser = argparse.ArgumentParser(
            description='docker-alias cli',
            usage=self.usage.format(
                add_description=self.add_description,
                build_description=self.build_description,
                list_description=self.list_description,
                remove_description=self.remove_description,
                run_description=self.run_description,
                version=VERSION
            )
        )
        parser.add_argument('command', help='Subcommand to run')
        parser.add_argument(
            '--quiet',
            default=False,
            action='store_true',
            help='outputs only std-out and std-err from docker-subprocess'
        )
        args = parser.parse_args(sys.argv[1:2])
        self.quiet = args.quiet
        if not hasattr(self, args.command):
            print('Unrecognized command')
            parser.print_help()
            sys.exit(1)
        getattr(self, args.command)()

    def add(self):
        parser = argparse.ArgumentParser(
            description=self.add_description
        )
        parser.add_argument('--path', help='optional path')
        args = parser.parse_args(sys.argv[2:])
        path = os.path.join(os.getcwd(), YAML_CONFIG_FILE_NAME)
        if args.path:
            path = args.path

        if not path.endswith(YAML_CONFIG_FILE_NAME):
            print('--path does not contain ' + YAML_CONFIG_FILE_NAME + '!')
            sys.exit(1)

        if not os.path.isfile(path):
            print(YAML_CONFIG_FILE_NAME + ' does not exist!')
            sys.exit(1)

        self.ini_config.add_yaml_path(path)
        print('Added ' + path + ' to config.ini')

    def remove(self):
        parser = argparse.ArgumentParser(
            description=self.remove_description
        )
        parser.add_argument('--path', help='optional path')
        args = parser.parse_args(sys.argv[2:])
        path = os.path.join(os.getcwd(), YAML_CONFIG_FILE_NAME)
        if args.path:
            path = args.path

        if not path.endswith(YAML_CONFIG_FILE_NAME):
            print('--path does not contain ' + YAML_CONFIG_FILE_NAME + '!')
            sys.exit(1)

        if not os.path.isfile(path):
            print(YAML_CONFIG_FILE_NAME + ' does not exist!')
            sys.exit(1)

        self.ini_config.remove_yaml_path(path)
        print('Removed ' + path + ' from config.ini')

    def list(self):
        container_util = ContainerUtil()
        argparse.ArgumentParser(description=self.list_description)

        containers = container_util.resolve_containers()
        containers.reverse()
        command_list = {}

        for container in containers:
            if not container.image:
                container.image = DockerUtil.image_name_pattern.format(
                    fs_location_hash=container.fs_location_hash,
                    container_name=container.name
                )
            if container.commands:
                for command in container.commands:
                    command_list[command.name] = " ".join(
                        DockerUtil(self.quiet).build_command(container, command=command)
                    )
            else:
                command_list[container] = " ".join(DockerUtil(self.quiet).build_command(container))

        for key, cmd in command_list.items():
            print(key + ": " + cmd)

    def run(self):
        container_util = ContainerUtil()
        parser = argparse.ArgumentParser(description=self.run_description, add_help=False)
        args, unknown = parser.parse_known_args(sys.argv[2:])
        if len(unknown) > 0:
            wanted_container = unknown[0]
            if '/' in wanted_container:
                wanted_container = wanted_container.split('/')[-1]
            unknown.pop(0)
            attributes = unknown
            for container in container_util.resolve_containers():
                if container.commands:
                    for command in container.commands:
                        if command.name == wanted_container:
                            sys.exit(DockerUtil(self.quiet).exec_docker(
                                container, command=command, attributes=attributes))
                if container.name == wanted_container:
                    sys.exit(DockerUtil(self.quiet).exec_docker(container, attributes=attributes))
            if not self.quiet:
                print('Container ' + wanted_container + ' not found!')
            sys.exit(1)

    def build(self):
        container_util = ContainerUtil()
        parser = argparse.ArgumentParser(description=self.build_description)
        parser.add_argument('container')
        args = parser.parse_args(sys.argv[2:])
        if args.container == 'all':
            for container in container_util.resolve_containers():
                if container.build:
                    DockerUtil(self.quiet).build_image(container)

        else:
            for container in container_util.resolve_containers():
                if container.build and container.name == args.container:
                    DockerUtil(self.quiet).build_image(container)


if __name__ == '__main__':
    try:
        DockerAliasCLI()
    except KeyboardInterrupt:
        pass
