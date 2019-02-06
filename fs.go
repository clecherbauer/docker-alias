package main

import (
	"crypto/md5"
	"encoding/hex"
	"io"
	"io/ioutil"
	"os"
	"os/user"
	"path"
	"path/filepath"
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

func getDockerAliasCachePath() string {
	user, _ := user.Current()
	return "/home/" + user.Username + "/.config/docker-alias"

}

func getServiceCacheFilePath(serviceName string) string {
	return getDockerAliasCachePath() + "/" + getCurrentProjectName() + "/" + serviceName
}

func getCurrentProjectName() string {
	path := findDockerComposePath()
	return filepath.Base(path)
}

func createDockerAliasProjectCacheDirectory() {
	dockerAliasProjectCachePath := getDockerAliasCachePath() + "/" + getCurrentProjectName()
	if _, err := os.Stat(dockerAliasProjectCachePath); os.IsNotExist(err) {
		os.MkdirAll(dockerAliasProjectCachePath, os.ModePerm)
	}
}

func serviceCacheFileExists(serviceName string) bool {
	if _, err := os.Stat(getServiceCacheFilePath(serviceName)); !os.IsNotExist(err) {
		return true
	}

	return false
}

func writeServiceCacheFile(serviceName string, content string) {
	createDockerAliasProjectCacheDirectory()
	serviceCacheFilePath := getServiceCacheFilePath(serviceName)
	ioutil.WriteFile(serviceCacheFilePath, []byte(content), 0644)
}

func getLastBuildTreeHash(serviceName string) string {
	if serviceCacheFileExists(serviceName) {
		buf, _ := ioutil.ReadFile(getServiceCacheFilePath(serviceName))
		return string(buf)
	}
	return ""
}

func calculateBuildTreeHash(relativeBuildWorkingDirectory string) string {
	buildWorkingDirectory := findDockerComposePath() + "/" + relativeBuildWorkingDirectory
	files := []string{}
	filepath.Walk(buildWorkingDirectory, func(path string, info os.FileInfo, err error) error {
		files = append(files, hashFileMd5(path))
		return nil
	})
	allFileHashes := strings.Join(files, "")
	hasher := md5.New()
	hasher.Write([]byte(allFileHashes))
	return hex.EncodeToString(hasher.Sum(nil))
}

func hashFileMd5(filePath string) string {
	var returnMD5String string
	file, err := os.Open(filePath)
	if err != nil {
		return returnMD5String
	}
	defer file.Close()
	hash := md5.New()
	if _, err := io.Copy(hash, file); err != nil {
		return returnMD5String
	}
	hashInBytes := hash.Sum(nil)[:16]
	returnMD5String = hex.EncodeToString(hashInBytes)
	return returnMD5String
}
