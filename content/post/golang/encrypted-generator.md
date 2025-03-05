+++
date = '2025-03-04T21:55:26-05:00'
draft = true
title = 'Encrypted Shellcode Injection'
+++

A tool to generate go source code to compile payloads utilizing encrypted shellcode injection. To be used with a template Go file to execute the encrypted shellcode.

---

## Encrypted Payload Generator
* Generate shellcode with msfvenom or other tools.
* Encrypt it using AES-256.
* Place the key and the encrypted shellcode into a template Go file.

Usage:</br>
`$ go run encrypted_payload_creator.go > payload.go`

```go
{{#include ../../assets/code/encrypted_payload_creator.go}}
```

## The Payload Template
* Used as a template Go file for the generator to include its encrypted shellcode and key.
* Decrypts shellcode with a given key and executes its memory via local code injection.

> <i class="fa fa-info-circle fa-lg"></i>
Be sure to set GOARCH to 32 or 64-bit depending on your payload when using msfvenom shellcode.

```
# Linux / Darwin
$ GOOS=windows GOARCH=386 go build encrypted_shellcode.go

# Windows
PS C:\> $Env:GOARCH=386; go build encrypted_shellcode.go
```

Encrypted Shellcode Template
```go
{{#include ../../assets/code/encrypted_shellcode_template.go}}
```

---

## References
- [tomsteele/penutils](https://github.com/tomsteele/pen-utils/blob/master/go-encrypt-shellcode-thing/main.go)
