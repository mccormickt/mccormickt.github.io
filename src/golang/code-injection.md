# Code Injection
Example of injecting shellcode into a local process.

---

## Calling the Windows API
To call the Windows API in Go, we need to use the `syscall` library to load `kernel32.dll` and create references to the functions we need to use. Additionally, we'll create some constants reflecting those that exist in the Windows API.

For shellcode injection, the `VirtualAlloc` Windows function is used to allocate memory in our process to store the payload.

```go
{{#include ../code/shellcode_injection.go:9:19}}
```
---

## Allocating memory and calling VirtualAlloc
Referencing documentation for the `VirtualAlloc` function in the C++ Windows API, we set our parameters to the `Call` function similarly in Go:

C++
```c++
LPVOID VirtualAlloc(
    LPVOID lpAddress,
    SIZE_T dwSize,
    DWORD  flAllocationType,
    DWORD  flProtect
);
```

Go
```go
{{#include ../code/shellcode_injection.go:25:31}}
```

Next, we write our shellcode into the allocated memory and execute it via a `syscall` at that memory address.

To copy the shellcode, we create a pointer reference to our allocated memory, `addr`, and cast it as a pointer to a large byte array.
After the payload is copied in, we can execute it with `syscall.Syscall()`, passing in our shellcode starting address:

```go
{{#include ../code/shellcode_injection.go:36:42}}
```

Since the msfvenom shellcode is 32-bit, we set the GOARCH environment variable accordingly to compile into a 32-bit executable. If all goes well, building and executing the source should show our shellcode is executed:


![Reverse Shell](../images/reverse_shell.png)
<p align=center>Catching the reverse shell launched via injected shellcode payload.</p>

---

## References
- [CreateRemoteThread Shellcode Injection](https://ired.team/offensive-security/code-injection-process-injection/process-injection)
- [Using Go to Call the Windows API](https://medium.com/jettech/breaking-all-the-rules-using-go-to-call-windows-api-2cbfd8c79724)
- [VirtualAlloc function - Win32 apps](https://docs.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualalloc?redirectedfrom=MSDN)


