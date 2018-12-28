package main

import (
	"io/ioutil"
	"strings"

	"github.com/smallfish/simpleyaml"
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
