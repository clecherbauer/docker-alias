package main

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"os/signal"
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

	for _, alias := range aliases {
		if alias.name == wantedAlias {
			arguments = buildRunArguments(alias)
		}
	}

	fmt.Println(fmt.Sprintf("Executing: %s", "docker-compose "+strings.Join(arguments[:], " ")))

	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt)

	cmd := exec.Command("docker-compose", arguments...)
	cmd.Stdin = os.Stdin
	cmd.Stdout = NewProxyWriter(os.Stdout)
	cmd.Stderr = NewProxyWriter(os.Stderr)

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
	cmd := exec.Command("docker-compose", "-f", calculateLevelsFromRoot()+"docker-alias.yml", "stop")
	cmd.Stdout = os.Stdout
	cmd.Run()
	cmd.Wait()
}
