+++
date = '2021-01-29T20:17:02-05:00'
draft = false
title = 'Reverse Shell'
tags = ['golang', 'security']
summary = 'A simple reverse shell implementation in Go that establishes a connection to a remote host and provides shell access across different operating systems.'
+++

> <i class="fa fa-info-circle fa-lg"></i>
To create a binary for a specific operating system or architecture, set the `GOOS` and `GOARCH` environment variables before running the `go build` command.<br/><br/>
`$ GOOS=$target_os GOARCH=$target_arch go build reverse_shell.go`

{{< include "reverse_shell.go" >}}

