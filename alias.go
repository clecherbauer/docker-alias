package main

import (
	"io/ioutil"
	"strings"

	"github.com/smallfish/simpleyaml"
)

type Alias struct {
	name      string
	service   string
	command   string
	user      string
	workdir   string
	keepRoot  bool
	buildPath string
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
		build, _ := yaml.GetPath("services", service, "build", "dockerfile").String()
		alias := Alias{}
		multiCommandAlias := false
		commands := []string{}

		if build != "" {
			alias.buildPath = build
		}

		for _, label := range labels {
			if strings.HasPrefix(label.(string), "com.docker-alias.name=") {
				nameValue := (strings.TrimPrefix(label.(string), "com.docker-alias.name="))
				if strings.HasPrefix(nameValue, "[") && strings.HasSuffix(nameValue, "]") {
					multiCommandAlias = true
					nameValue = strings.Replace(nameValue, " ", "", -1)
					nameValue = strings.Trim(nameValue, "com.docker-alias.name=")
					nameValue = strings.Trim(nameValue, "[")
					nameValue = strings.Trim(nameValue, "]")
					commands = strings.Split(nameValue, ",")
				} else {
					alias.name = nameValue
				}
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
			if multiCommandAlias == false {
				if alias.command == "" {
					alias.command = alias.name
				}
				aliases = append(aliases, alias)
			} else {
				for _, command := range commands {
					alias.name = command
					alias.command = command
					aliases = append(aliases, alias)
				}
			}
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
