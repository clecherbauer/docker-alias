package main

import (
    
    "github.com/smallfish/simpleyaml"
    "io/ioutil"
    "os"
    "fmt"
    "strings"
    //github.com/davecgh/go-spew/spew"
    "sort"
)

type Alias struct {
    name string
    service string
    command string
}

func getAliases() []Alias {
    path := os.Args[2]
    filename := path + "/docker-compose.alias.yml"
    source, err := ioutil.ReadFile(filename)
    yaml, err := simpleyaml.NewYaml(source)
    services, err := yaml.Get("services").Map()
    aliases := make([]Alias, 0)

    for service := range services {
        labels, err := yaml.GetPath("services", service, "labels").Array()
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

            if (alias.service == "") {
                alias.service = service.(string)
            }

            if (alias.command == "") {
                alias.command = alias.name
            }

        }
        aliases = append(aliases, alias)

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
    rootDir := os.Args[2]

    filePaths,_ := ioutil.ReadDir(rootDir)

    for _, filePath := range filePaths {
        if (filePath.Name() == "docker-compose.yml" || filePath.Name() == "docker-compose.override.yml") {
            validFiles = append(validFiles, filePath.Name())
        }
    }

    sort.Sort(sort.Reverse(sort.StringSlice(validFiles)))

    return validFiles
}

func calculatePathSegment() string {
    currentDir, _ := os.Getwd()
    rootDir := os.Args[2]

    segment := strings.TrimPrefix(currentDir, rootDir)
    if (segment == "") {
        return "./"
    }

    return strings.TrimPrefix(segment, "/")
}

func buildCommand(alias Alias, dcfs string) string {
    return alias.name + "=docker-compose" + dcfs + " run --rm " + alias.service + " bash -c \"cd " + calculatePathSegment() + " && " + alias.command + "\""
}

func listNames() {
    aliases := getAliases()
    for _, alias := range aliases {
        fmt.Println(alias.name)
    }
    fmt.Println("docker-show-alias")
}

func listCommands() {
    aliases := getAliases()
    dockerComposeFiles := findDockerComposeFiles()
    dockerComposeFileString := ""

    for _, dockerComposeFile := range dockerComposeFiles {
        dockerComposeFileString = dockerComposeFileString + " -f " + dockerComposeFile
    }
    dockerComposeFileString = dockerComposeFileString + " -f docker-compose.alias.yml"

    for _, alias := range aliases {
        fmt.Println(buildCommand(alias, dockerComposeFileString))
    }

    fmt.Println("docker-show-alias=alias|grep \"docker-compose -f\" --color=never")
}

func main() {
    if (os.Args[1] == "list-names") {
        listNames()
    }
    if (os.Args[1] == "list-commands") {
        listCommands()
    }

}