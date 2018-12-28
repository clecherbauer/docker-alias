package main

import (
	"os"
)

type ProxyWriter struct {
	file *os.File
}

func NewProxyWriter(file *os.File) *ProxyWriter {
	return &ProxyWriter{
		file: file,
	}
}

func (w *ProxyWriter) Write(p []byte) (int, error) {
	return w.file.Write(p)
}

func appendAdditionalParameters(commandParts []string) []string {
	if len(os.Args) > 3 {
		for i := 3; i < len(os.Args); i++ {
			commandParts = append(commandParts, os.Args[i])
		}
	}

	return commandParts
}
