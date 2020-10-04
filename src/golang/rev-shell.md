# Reverse Shell

> <i class="fa fa-info-circle fa-lg"></i>
To create a binary for a specific operating system or architecture, set the `GOOS` and `GOARCH` environment variables before running the `go build` command.<br/><br/>
`$ GOOS=$target_os GOARCH=$target_arch go build reverse_shell.go`

```go
{{#include ../code/reverse_shell.go}}
```
