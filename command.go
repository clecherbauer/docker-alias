package main

import (
	"os"
)

func appendAdditionalParameters(commandParts []string) []string {
	if len(os.Args) > 3 {
		for i := 3; i < len(os.Args); i++ {
			commandParts = append(commandParts, os.Args[i])
		}
	}

	return commandParts
}
