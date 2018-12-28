package main

import (
	"io/ioutil"
	"os"
	"path"
	"regexp"
	"sort"
	"strings"
)

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
