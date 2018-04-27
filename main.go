package main

import (
	"bytes"
	"fmt"
	"io/ioutil"
	"os"
	"strings"

	"github.com/smallfish/simpleyaml"
	//"github.com/davecgh/go-spew/spew"
	"os/exec"
	"path"
	"regexp"
	"sort"
)

type Alias struct {
	name     string
	service  string
	command  string
	user     string
	workdir  string
	keepRoot bool
}

func getAliases() []Alias {
	path := findDockerComposePath()
	filename := path + "/docker-alias.yml"
	source, err := ioutil.ReadFile(filename)
	yaml, err := simpleyaml.NewYaml(source)
	services, err := yaml.Get("services").Map()
	aliases := make([]Alias, 0)

	for service := range services {
		labels, _ := yaml.GetPath("services", service, "labels").Array()
		alias := Alias{}
		for _, label := range labels {
			if strings.HasPrefix(label.(string), "com.docker-alias.name=") {
				alias.name = (strings.TrimPrefix(label.(string), "com.docker-alias.name="))
			}
			if strings.HasPrefix(label.(string), "com.docker-alias.service=") {
				alias.service = (strings.TrimPrefix(label.(string), "com.docker-alias.service="))
			}
			if strings.HasPrefix(label.(string), "com.docker-alias.command=") {
				alias.command = (strings.TrimPrefix(label.(string), "com.docker-alias.command="))
			}
			if strings.HasPrefix(label.(string), "com.docker-alias.user=") {
				alias.user = (strings.TrimPrefix(label.(string), "com.docker-alias.user="))
			}
			if strings.HasPrefix(label.(string), "com.docker-alias.keepRoot=true") {
				alias.keepRoot = true
			}
		}

		workdir := ""
		if yaml.GetPath("services", service, "working_dir").IsFound() {
			workdir, _ = yaml.GetPath("services", service, "working_dir").String()
		}
		alias.workdir = workdir

		if (alias != Alias{}) {
			if alias.service == "" {
				alias.service = service.(string)
			}

			if alias.command == "" {
				alias.command = alias.name
			}

			aliases = append(aliases, alias)
		}

		if err != nil {
			panic(err)
		}
	}

	if err != nil {
		panic(err)
	}

	return aliases
}

func findDockerComposeFiles() []string {
	var validFiles []string
	rootDir := findDockerComposePath()

	filePaths, _ := ioutil.ReadDir(rootDir)

	for _, filePath := range filePaths {
		if filePath.Name() == "docker-compose.yml" || filePath.Name() == "docker-compose.override.yml" {
			validFiles = append(validFiles, filePath.Name())
		}
	}

	sort.Sort(sort.Reverse(sort.StringSlice(validFiles)))

	return validFiles
}

func findDockerComposePath() string {
	fileName := "docker-alias.yml"
	foundPath := ""
	currentPath, _ := os.Getwd()

	for currentPath != "/" {
		if _, err := os.Stat(currentPath + "/" + fileName); os.IsNotExist(err) {
			currentPath = path.Dir(currentPath)
		} else {
			foundPath = currentPath
			break
		}
	}

	return foundPath
}

func calculatePathSegment() string {
	currentDir, _ := os.Getwd()
	rootDir := findDockerComposePath()
	segment := strings.TrimPrefix(currentDir, rootDir)

	return strings.TrimPrefix(segment, "/")
}

func calculateLevelsFromRoot() string {
	currentDir, _ := os.Getwd()
	aORb := regexp.MustCompile("/")
	matchesFromRoot := aORb.FindAllStringIndex(strings.TrimSuffix(findDockerComposePath(), "/"), -1)
	matchesFromCurrentDir := aORb.FindAllStringIndex(strings.TrimSuffix(currentDir, "/"), -1)
	diffrence := 0
	if len(matchesFromRoot) < len(matchesFromCurrentDir) {
		diffrence = len(matchesFromCurrentDir) - len(matchesFromRoot)
	}

	levels := ""
	for i := 0; i < diffrence; i++ {
		levels = levels + "../"
	}

	return levels
}

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

func appendAdditionalParameters(commandParts []string) []string {
	if len(os.Args) > 3 {
		for i := 3; i < len(os.Args); i++ {
			commandParts = append(commandParts, os.Args[i])
		}
	}

	return commandParts
}

func buildCommand(alias Alias) []string {
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
	commandParts = append(commandParts, alias.command)
	commandParts = appendAdditionalParameters(commandParts)

	return commandParts
}

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
		command := buildCommand(alias)
		fmt.Println(alias.name + " = docker-compose " + strings.Join(command[:], " "))
	}
}

func runAlias() {
	aliases := getAliases()
	wantedAlias := os.Args[2]
	var command []string

	for _, alias := range aliases {
		if alias.name == wantedAlias {
			command = buildCommand(alias)
		}
	}

	fmt.Println(fmt.Sprintf("Executing: %s", "docker-compose "+strings.Join(command[:], " ")))

	cmd := exec.Command("docker-compose", command...)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Run()
	cmd.Wait()
	shutDownRemainingServices()
	removeVolume()
}

func removeVolume() {
	cmd := exec.Command("docker", "volume", "ls", "--filter", "label=com.docker-alias=true", "--quiet")
	cmdOutput := &bytes.Buffer{}
	cmd.Stdout = cmdOutput
	cmd.Stderr = os.Stderr

	cmd.Run()
	cmd.Wait()

	lines := strings.Split(cmdOutput.String(), "\n")
	for _, line := range lines {
		if line != "" {
			subCmd := exec.Command("docker", "volume", "rm", line)
			subCmd.Stderr = os.Stderr
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

func main() {
	if len(os.Args) > 1 {
		projectRoot := findDockerComposePath()
		if os.Args[1] == "find-project-root" {
			fmt.Println(projectRoot)
		}
		if projectRoot == "" {
			return
		}
		if os.Args[1] == "list-names" {
			listNames()
		}
		if os.Args[1] == "list-aliases" {
			listAliases()
		}
		if os.Args[1] == "list-commands" {
			listCommands()
		}
		if os.Args[1] == "run-alias" {
			runAlias()
		}
	} else {
		fmt.Println("Usage: docker-alias [find-project-root | list-names | list-aliases | list-commands | run-alias]")
	}
}
