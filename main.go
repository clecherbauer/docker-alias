package main

import (
    
    "github.com/smallfish/simpleyaml"
    "io/ioutil"
    "os"
    "fmt"
    "strings"
    //"github.com/davecgh/go-spew/spew"
    "sort"
    "regexp"
    "path"
    "os/exec"
)

type Alias struct {
    name string
    service string
    command string
    user string
}

func getAliases() []Alias {
    path := findDockerComposePath()
    filename := path + "/docker-compose.alias.yml"
    source, err := ioutil.ReadFile(filename)
    yaml, err := simpleyaml.NewYaml(source)
    services, err := yaml.Get("services").Map()
    aliases := make([]Alias, 0)

    for service := range services {
        labels, _ := yaml.GetPath("services", service, "labels").Array()
        alias := Alias{}
        for _, label := range labels {
            if (strings.HasPrefix(label.(string), "com.docker-alias.name=")) {
                alias.name = (strings.TrimPrefix(label.(string), "com.docker-alias.name="))
            }
            if (strings.HasPrefix(label.(string), "com.docker-alias.service=")) {
                alias.service = (strings.TrimPrefix(label.(string), "com.docker-alias.service="))
            }
            if (strings.HasPrefix(label.(string), "com.docker-alias.command=")) {
                alias.command = (strings.TrimPrefix(label.(string), "com.docker-alias.command="))
            }
            if (strings.HasPrefix(label.(string), "com.docker-alias.user=")) {
                alias.user = (strings.TrimPrefix(label.(string), "com.docker-alias.user="))
            }
        }

        if (alias != Alias{}) {
            if (alias.service == "") {
                alias.service = service.(string)
            }
    
            if (alias.command == "") {
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

    filePaths,_ := ioutil.ReadDir(rootDir)

    for _, filePath := range filePaths {
        if (filePath.Name() == "docker-compose.yml" || filePath.Name() == "docker-compose.override.yml") {
            validFiles = append(validFiles, filePath.Name())
        }
    }

    sort.Sort(sort.Reverse(sort.StringSlice(validFiles)))

    return validFiles
}

func findDockerComposePath() string {
    fileName := "docker-compose.alias.yml"
    foundPath := ""
    currentPath, _ := os.Getwd()

    for currentPath != "/" {
        if _, err := os.Stat(currentPath + "/" + fileName); os.IsNotExist(err) {
            currentPath = path.Dir(currentPath)
        } else {
            foundPath = currentPath
            break;
        }
    }

    return foundPath
}

func calculatePathSegment() string {
    currentDir, _ := os.Getwd()
    rootDir := findDockerComposePath()

    segment := strings.TrimPrefix(currentDir, rootDir)
    if (segment == "") {
        return "./"
    }

    return strings.TrimPrefix(segment, "/")
}

func calculateLevelsFromRoot() string {
    currentDir, _ := os.Getwd()
    aORb := regexp.MustCompile("/")
	matchesFromRoot := aORb.FindAllStringIndex(strings.TrimSuffix(findDockerComposePath(), "/"), -1)
    matchesFromCurrentDir  := aORb.FindAllStringIndex(strings.TrimSuffix(currentDir, "/"), -1)
    diffrence := 0
	if (len(matchesFromRoot) < len(matchesFromCurrentDir)) {
		diffrence = len(matchesFromCurrentDir) - len(matchesFromRoot)
    }
    
    levels := ""
    for i := 0; i < diffrence; i++  {
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
        dockerComposeFileStrings = append(dockerComposeFileStrings, levelsFromRootString + dockerComposeFile)
    }

    dockerComposeFileStrings = append(dockerComposeFileStrings, "-f")
    return append(dockerComposeFileStrings, levelsFromRootString + "docker-compose.alias.yml")
}

func buildAdditionalParameterString() string {
    command := ""
    if (len(os.Args) > 3) {
        for i := 3; i < len(os.Args); i++ {
            command = command + " " + os.Args[i]
        }
    }   

    return command
}

func buildCommand(alias Alias) []string {
    dockerComposeFileStrings := buildDockerComposeFileStrings()
    var commandParts []string

    for _, dockerComposeFileString := range dockerComposeFileStrings {
        commandParts = append(commandParts, dockerComposeFileString)
    }
    commandParts = append(commandParts, "run")
    commandParts = append(commandParts, "--rm")

    if (alias.user != "") {
        commandParts = append(commandParts, "-u")
        commandParts = append(commandParts, alias.user)
    }

    commandParts = append(commandParts, alias.service)
    commandParts = append(commandParts, "bash")
    commandParts = append(commandParts, "-c")
    commandParts = append(commandParts, "cd " + calculatePathSegment() + "; " + alias.command + buildAdditionalParameterString())

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
        fmt.Println( alias.name + " = docker-compose " + strings.Join(command[:], " "))
    }
}

func runAlias() {
    aliases := getAliases()
    wantedAlias := os.Args[2]
    var command []string

    for _, alias := range aliases {
        if ( alias.name == wantedAlias) {
            command = buildCommand(alias)
        }
    }

    fmt.Println(fmt.Sprintf("Executing: %s", "docker-compose " + strings.Join(command[:], " ")))

    cmd := exec.Command("docker-compose", command...)
    cmd.Stdout = os.Stdout
    cmd.Stderr = os.Stderr
    cmd.Run()
}

func main() {
    if (len(os.Args) > 1) {
        projectRoot := findDockerComposePath()
        if (os.Args[1] == "find-project-root") {
            fmt.Println(projectRoot)
        }
        if (projectRoot == "") {
            return 
        }
        if (os.Args[1] == "list-names") {
            listNames()
        }
        if (os.Args[1] == "list-aliases") {
            listAliases()
        }
        if (os.Args[1] == "list-commands") {
            listCommands()
        }
        if (os.Args[1] == "run-alias") {
            runAlias()
        }
    } else {
        fmt.Println("Usage: docker-alias [find-project-root | list-names | list-aliases | list-commands | run-alias]")
    }
}