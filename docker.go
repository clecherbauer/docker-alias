package main

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"strings"
)

func buildDockerComposeFileStrings() []string {
	dockerComposeFiles := findDockerComposeFiles()
	levelsFromRootString := calculateLevelsFromRoot()
	var dockerComposeFileStrings []string

	for _, dockerComposeFile := range dockerComposeFiles {
		dockerComposeFileStrings = append(dockerComposeFileStrings, "-f")
		dockerComposeFileStrings = append(dockerComposeFileStrings, levelsFromRootString+dockerComposeFile)
	}

	dockerComposeFileStrings = append(dockerComposeFileStrings, "-f")
	return append(dockerComposeFileStrings, levelsFromRootString+"docker-alias.yml")
}

func buildRunArguments(alias Alias) []string {
	dockerComposeFileStrings := buildDockerComposeFileStrings()
	var commandParts []string

	for _, dockerComposeFileString := range dockerComposeFileStrings {
		commandParts = append(commandParts, dockerComposeFileString)
	}
	commandParts = append(commandParts, "run")
	commandParts = append(commandParts, "--rm")

	if alias.user != "" {
		commandParts = append(commandParts, "-u")
		commandParts = append(commandParts, alias.user)
	}

	if alias.keepRoot == false {
		commandParts = append(commandParts, "-w")
		commandParts = append(commandParts, alias.workdir+"/"+calculatePathSegment())
	}

	if alias.detach == true {
		commandParts = append(commandParts, "-d")
	}

	commandParts = append(commandParts, alias.service)

	aliasCommandParts := strings.Split(alias.command, " ")
	for _, aliasCommandPart := range aliasCommandParts {
		commandParts = append(commandParts, aliasCommandPart)
	}
	commandParts = appendAdditionalParameters(commandParts)

	return commandParts
}

func buildRebuildArguments(alias Alias) []string {
	dockerComposeFileStrings := buildDockerComposeFileStrings()
	var commandParts []string

	for _, dockerComposeFileString := range dockerComposeFileStrings {
		commandParts = append(commandParts, dockerComposeFileString)
	}
	commandParts = append(commandParts, "build")

	commandParts = append(commandParts, alias.service)

	return commandParts
}

func rebuildAliasContainers() {
	aliases := getAliases()

	for _, alias := range aliases {
		var arguments = buildRebuildArguments(alias)

		fmt.Println(fmt.Sprintf("Executing: %s", "docker-compose "+strings.Join(arguments[:], " ")))

		cmd := exec.Command("docker-compose", arguments...)
		cmd.Stdout = NewProxyWriter(os.Stdout)
		cmd.Stderr = NewProxyWriter(os.Stderr)
		cmd.Run()
		cmd.Wait()
	}
}

func rebuildAliasContainer(aliasName string) {
	currentAlias := Alias{}
	aliases := getAliases()
	for _, alias := range aliases {
		if alias.name == aliasName {
			currentAlias = alias
		}
	}

	var arguments = buildRebuildArguments(currentAlias)

	fmt.Println(fmt.Sprintf("Executing: %s", "docker-compose "+strings.Join(arguments[:], " ")))

	cmd := exec.Command("docker-compose", arguments...)
	cmd.Stdout = NewProxyWriter(os.Stdout)
	cmd.Stderr = NewProxyWriter(os.Stderr)
	cmd.Run()
	cmd.Wait()
}

func runAlias() {
	aliases := getAliases()
	wantedAlias := os.Args[2]
	var arguments []string
	var alias Alias

	for _, availableAlias := range aliases {
		if availableAlias.name == wantedAlias {
			alias = availableAlias
		}
	}

	arguments = buildRunArguments(alias)

	if alias.buildPath != "" {
		hash := calculateBuildTreeHash(filepath.Dir(alias.buildPath))

		if !serviceCacheFileExists(alias.service) {
			writeServiceCacheFile(alias.service, hash)
			rebuildAliasContainer(alias.name)
		} else {
			if hash != getLastBuildTreeHash(alias.service) {
				writeServiceCacheFile(alias.service, hash)
				rebuildAliasContainer(alias.name)
			}
		}
	}
	if alias.silent == false {
		fmt.Println(fmt.Sprintf("Executing: %s", "docker-compose "+strings.Join(arguments[:], " ")))
	}

	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt)

	cmd := exec.Command("docker-compose", arguments...)
	cmd.Stdin = os.Stdin
	if alias.silent == false {
		cmd.Stdout = NewProxyWriter(os.Stdout)
		cmd.Stderr = NewProxyWriter(os.Stderr)
	}

	go func() {
		for {
			select {
			case <-c:
				fmt.Println("")
				fmt.Println("Killing process")
				cmd.Process.Kill()
			}
		}
	}()

	if len(alias.preExecutionCommand) > 0 {
		var preCmdArguments []string
		preCmdArguments = strings.Split(alias.preExecutionCommand, " ")

		preCmd := exec.Command(preCmdArguments[0], preCmdArguments[:0]...)
		preCmd.Stdin = os.Stdin
		if alias.silent == false {
			preCmd.Stdout = NewProxyWriter(os.Stdout)
		}
		preCmd.Stderr = NewProxyWriter(os.Stderr)
		preCmd.Run()
		preCmd.Wait()
	}

	cmd.Run()
	cmd.Wait()
	shutDownRemainingServices()
	removeVolume()
}

func removeVolume() {
	cmd := exec.Command("docker", "volume", "ls", "--filter", "label=com.docker-alias=true", "--quiet")
	cmdOutput := &bytes.Buffer{}
	cmd.Stdout = cmdOutput
	cmd.Run()
	cmd.Wait()

	lines := strings.Split(cmdOutput.String(), "\n")
	for _, line := range lines {
		if line != "" {
			subCmd := exec.Command("docker", "volume", "rm", line)
			subCmd.Run()
			subCmd.Wait()
		}
	}
}

func shutDownRemainingServices() {
	_, services, _ := getServices()

	for service := range services {
		var arguments = buildDockerComposeFileStrings()
		arguments = append(arguments, "stop")
		arguments = append(arguments, service.(string))
		cmd := exec.Command("docker-compose", arguments...)
		cmd.Run()
		cmd.Wait()
	}
}

func clean() {
	_, services, _ := getServices()

	for service := range services {
		var arguments = buildDockerComposeFileStrings()
		arguments = append(arguments, "rm")
		arguments = append(arguments, "-f")
		arguments = append(arguments, "-s")
		arguments = append(arguments, "-v")
		arguments = append(arguments, service.(string))
		cmd := exec.Command("docker-compose", arguments...)
		cmd.Run()
		cmd.Wait()
	}
}
