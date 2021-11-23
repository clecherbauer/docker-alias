package main

import (
	"fmt"
	"os"
	"strings"
)

// version of this tool
const version = "1.3.0"

func listNames() {
	aliases := getAliases()

	for _, alias := range aliases {
		fmt.Println(alias.name)
	}
}

func listAliases() {
	aliases := getAliases()

	for _, alias := range aliases {
		fmt.Println(alias.name + "=docker-alias run-alias " + alias.name)
	}
}

func listCommands() {
	aliases := getAliases()

	for _, alias := range aliases {
		command := buildRunArguments(alias)
		fmt.Println(alias.name + " = docker-compose " + strings.Join(command[:], " "))
	}
}

func main() {
	if len(os.Args) > 1 {
		projectRoot := findDockerComposePath()
		if os.Args[1] == "find-project-root" {
			fmt.Println(projectRoot)
			return
		}
		if projectRoot == "" {
			return
		}
		if os.Args[1] == "list-names" {
			listNames()
			return
		}
		if os.Args[1] == "list-aliases" {
			listAliases()
			return
		}
		if os.Args[1] == "list-commands" {
			listCommands()
			return
		}
		if os.Args[1] == "run-alias" {
			runAlias()
			return
		}
		if os.Args[1] == "build" {
			if len(os.Args) == 3 {
				rebuildAliasContainer(os.Args[2])
				return
			}

			rebuildAliasContainers()
			return
		}
		if os.Args[1] == "clean" {
			clean()
			return
		}
	}

	printUsage()
}

func printUsage() {
	fmt.Println(os.Args[0] + " requires at least 1 argument")
	fmt.Println("")
	fmt.Println("Usage: " + os.Args[0] + " [argument]")
	fmt.Println("")
	fmt.Println("Available Options:")
	fmt.Println(" list-names		List the name of all services")
	fmt.Println(" list-aliases		List the shell-alias of all services")
	fmt.Println(" list-commands		List the command wich is used to execute the services")
	fmt.Println(" run-alias [name] ...	Run an alias by name an pass additional arguments to container")
	fmt.Println(" build		Build all service containers")
	fmt.Println(" build [name]		Build a specific service container by name")
	fmt.Println(" clean			Remove old Containers e.g. due to detached mode")
	fmt.Println("")
	fmt.Println("This tool depends on: docker and docker-compose")
	fmt.Println("")
	fmt.Println("Version: " + version)
	fmt.Println("")
	fmt.Println("This reads services from docker-alias.yml (docker-compose style)")
}
