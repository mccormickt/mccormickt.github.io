+++
date = '2025-03-04T21:55:26-05:00'
draft = true
title = 'Exif Parser Fuzzing'
+++

Writing a custom fuzzer for an exif parser using Go.

---

## Easy Fuzzing Target
A light google search of common fuzzing targets implemented in memory-unsafe languages such as C leads me to find [this](https://github.com/mkttanabe/exif/) repo. It's a great, simple implementation of an exif parser and will work perfectly for our purposes.

To test the output of the tool, compile the binary and run it on a sample jpg containing exif data. A great sample set can be found at https://github.com/ianare/exif-samples.

```
~/exifFuzz/exif $ make
~/exifFuzz/exif $ ./exif ../exif-samples/Canon_40D.jpg

[Canon_40D.jpg] createIfdTableArray: result=4

{0TH IFD}
 - Make: [Apple]
 - Model: [iPod touch]
 - Orientation: 1
... snip ...
```

## Designing the Fuzzer
Fuzzing in general is all about rapidly varying the inputs of an application. In this case, all the data we have to manipulate is the contents of our input file. Randomly chaning individual bytes or patterns in the input file is bound to produce some unexpected results. This means our fuzzer will need to perform the following actions:
- Read in the bytes of a file.
- Manipulate the bytes of a file in various ways.
- Save the new mutated file.
- Run the exif binary on the mutated file.
- Detect interesting crashes of the program.
- Save the output of these crashes to a file with a meaningful name.
- Repeat many many times.
---

## File Operations
To manipulate the bytes of an input file, we use the `ioutil` package. We'll create two functions, `getBytes` and `createNew` that we will use to read the input file into a slice of bytes and then create a new file after we've mutated them. We can also include a small function, check that we use to check error values.

These helper functions are done simply:

```go
// Check and panic on error
func check(e error) {
    if e != nil {
    panic(e)
    }
}

// Retrieve bytes from `filename`
func getBytes(filename string) []byte {
    f, err := ioutil.ReadFile(filename)
    check(err)
    return f
}

// Create new file with `data`
func createNew(data []byte) {
    err := ioutil.WriteFile("mutated.jpg", data, 0644)
    check(err)
}
```

## Input File Mutation

### The Bit Flip
An easy way to change input data is a simple bit flip. To implement this, I decided I would randomly select a percentage of the bytes in the file, and of that subset I'd change a byte randomly. This is slightly different than changing a singular bit randomly throughout the file, however I felt it achieved generally the same effect.

To begin we'll need to select bytes at random, keeping track of their indexes in the input byte slice. We subtract 4 bytes off of the the file length to account for the `FF D8 FF DB` jpg file header.

```go
var byteIndexes []int
numBytes := int(float64(len(data)-4) * .01)
for len(byteIndexes) < numBytes {
    // For random ints in range = rand.Intn(Max - Min) + Min
    byteIndexes = append(byteIndexes, rand.Intn((len(data)-4)-4)+4)
}
fmt.Println("Indexes chosen: ", byteIndexes)
```

Knowing these indexes, we'll then loop through the data and change the values of the target bytes, and return the mutated byte slice.

```go
// Randomly change the bytes at the location of the chosen indexes
    for _, index := range byteIndexes {
        oldbytes := data[index]
        newbytes := byte(rand.Intn(0xFF))
        data[index] = newbytes
        fmt.Printf("Changed %x to %x\n", oldbytes, newbytes)
    }
    return data
```

### Getting More Sophisticated - Magic Numbers

Since I generally don't know what I'm doing, I tend to read many blogs and watch technology streams to discover techniques in areas that I'm unfamiliar with - like Fuzzing! [Gynvael's YouTube channel](https://twitter.com/gynvael) has loads of resources on fuzzing and is a great resource for learning more. In his intro to fuzzing stream, he mentions "Magic Numbers" in files that are ripe for manipulation.

The numbers are chosen based on the propensity for errors like integer underflow or overflow to result from changing their values.
- `0xFF`
- `0x7F`
- `0x00`
- `0xFFFF`
- `0x0000`
- `0xFFFFFFFF`
- `0x00000000`
- `0x80000000` (Minimum 32-bit integer)
- `0x40000000` (1/2 Min 32-bit integer)
- `0x7FFFFFFF` (Maximum 32-bit integer)

For example, if `0x7FFFFFFF` is chosen as the value to replace, we'll have to replace the first byte with `0x7F` and then each subsequent byte with `0xFF` for a total of 4 bytes in length.

We'll construct a mapping for these values in a slice of int slices, and then pick a set at random to tell us what to change in the input data.

```go
// Gynvael's magic numbers https://www.youtube.com/watch?v=BrDujogxYSk&
magicVals := [][]int{
    {1, 255},
    {1, 255},
    {1, 127},
    {1, 0},
    {2, 255},
    {2, 0},
    {4, 255},
    {4, 0},
    {4, 128},
    {4, 64},
    {4, 127},
}

pickedMagic := magicVals[rand.Intn(len(magicVals))]
index := rand.Intn(len(data) - 8)
```

We'll then just hard-code our values into a switch statement to change the input data according to the value selected:

```go
// Hardcode byte overwrites for tuples beginning with (1, )
    if pickedMagic[0] == 1 {
        switch pickedMagic[1] {
        case 255:
            data[index] = 255
        case 127:
            data[index+1] = 127
        case 0:
            data[index] = 0
        }
        // Hardcode byte overwrites for tuples beginning with (2, )
        } else if pickedMagic[0] == 2 {
            switch pickedMagic[1] {
        case 255:
            data[index] = 255
            data[index+1] = 255
        case 0:
            data[index] = 0
            data[index+1] = 0
        }
        // Hardcode byte overwrites for tuples beginning with (4, )
        } else if pickedMagic[0] == 4 {
            switch pickedMagic[1] {
            case 255:
                data[index] = 255
                data[index+1] = 255
                data[index+2] = 255
                data[index+3] = 255
            case 0:
                data[index] = 0
                data[index+1] = 0
                data[index+2] = 0
                data[index+3] = 0
            case 128:
                data[index] = 128
                data[index+1] = 0
                data[index+2] = 0
                data[index+3] = 0
            case 64:
                data[index] = 64
                data[index+1] = 0
                data[index+2] = 0
                data[index+3] = 0
            case 127:
                data[index] = 127
                data[index+1] = 255
                data[index+2] = 255
                data[index+3] = 255
            }
    }
    return data
}
```

## Randomize Mutations

To round out our mutation routines, and because our bit flipper isn't entirely obsolete (or at least I like to think it isn't), we can create one last wrapper function for mutating data. This wrapper will randomize our choice of mutator between the `mutateMagic` and `mutateBits` techniques.

```go
// Select mutator at random to mutate `data`
func mutate(data []byte) []byte {
    mutators := []func([]byte) []byte{mutateBits, mutateMagic}
    return mutators[rand.Intn(len(mutators))](data)
}
```
---

## Writing the Fuzzing Harness
Now for the real meat of the fuzzer. We need to feed the program our mutated file, and keep track of inputs that cause significant crashes. A significant crash in this case would be writing to memory outside of the range of the program, or a segmentation fault.

To easily capture the error output of a faulting instance of `exif`, we wrap the command in a `bash -c` command, and execute it with Go using the `os/exec` package. We then direct the `stderr` from the command to our buffer to analyze the output.

```go
// Run command, capture output
var output bytes.Buffer
exifCommand := "/bin/bash"
cmd := exec.Command(exifCommand, "-c", "./exif/bin/exif ./mutated.jpg -verbose")
cmd.Stderr = &output
err := cmd.Start()
check(err)
```

We make sure to include a counter value in our wrapper program so we can determine which run created which error. If we find an iteration has exited in error,  we check our error buffer for evidence of a segfault. When we find a segfault, write the input data as a jpg, labeled with the fuzzing iteration.

```go
// Write any crashes to file
if err := cmd.Wait(); err != nil {
    if exitError, ok := err.(*exec.ExitError); ok {
        // Check if error is a segfault
        if strings.Contains(exitError.String(), "segmentation") {
            // Write falt-causing `data` to jpg file, label with `counter`
            fmt.Printf("%d - %s\n", counter, exitError)
            err = ioutil.WriteFile(fmt.Sprintf("./crashes/crash.%d.jpg", counter), data, 0644)
            check(err)
        }
    }
}

// Print `counter` as status updates
if counter%100 == 0 {
    fmt.Println(counter)
}
```

## Putting it all Together
Now we're ready to create the main execution flow of our fuzzing routine. Looking back at what we set out to do, we see where each piece fits in:

 - Read in the bytes of a file. ✔ `getBytes`
 - Manipulate the bytes of a file in various ways. ✔ `mutateMagic`, `mutateBits`
 - Save the new mutated file. ✔ `mutate`
 - Run the exif binary on the mutated file. ✔ `exif`
 - Detect interesting crashes of the program. ✔ `exif`
 - Save the output of these crashes to a file with a meaningful name. ✔ `exif`
 - Repeat many many times.

Easy! All we need to do is run this through a loop and make it command-line ready with a `main` such as:

```go
func main() {
    if len(os.Args) < 2 {
        fmt.Println("Usage: go exifFuzz.go <valid_jpg>")
        os.Exit(1)
    }

    // Create mutated file
    filename := os.Args[1]
    for counter := 0; counter < 100000; counter++ {
    data := getBytes(filename)
    mutated := mutate(data)
    createNew(mutated)
    exif(counter, mutated)
    }
}
```

Running our code gives us updates as it runs, and will start filling the crashes/ directory with jpg data that caused the program to segfault. As it executes iterations of the binary, you'll see it pick up some segfaults.

```
~/exifFuzz $ go build
~/exifFuzz $ ./exifFuzz exif-samples/jpg/Canon_40D.jpg
0
19 - signal: segmentation fault
65 - signal: segmentation fault
66 - signal: segmentation fault
... snip ...
```

Once our fuzzer is done, we can confirm the accuracy of our crash data by trying one out ourselves:

```
~/exifFuzz $ ./exif/bin/exif crashes/crash.2436.jpg
Segmentation fault
```

## Conclusion
My experience with Go is that it is an extremely versatile and easy to learn language, with powerful low-level capabilities. Finding tools and solutions in one language and implementing them in Go is rather straightforward, and a great way to learn more, no what matter the source language is. This is a great example of a highly-documented use case that is a great exercise for learning a new language. This fuzzer can definitely be improved upon with [goroutines](https://tour.golang.org/concurrency/1) for concurrency among many other optimizations for performance. We'll see what we can do in the future to implement concurrency into our fuzzer, or possibly implement it again in a more performant type-safe language such as Rust. Additionally, we could go down the route of exploitation, and explore ways of identifying vulnerabilities brought to light by our fuzzer.

The full source of this lab can be found on my [Github](https://github.com/jan0ski/exifFuzz). It includes everything needed for the steps covered here (including a version for the win32 binary!).

---

## References
- [h0mbre - Fuzzing Like A Caveman](https://h0mbre.github.io/Fuzzing-Like-A-Caveman/#)
- [jaybosamiya - Security Notes](https://github.com/jaybosamiya/security-notes#basics-of-fuzzing)
- [Gynvael's Youtube Channel](https://www.youtube.com/channel/UCCkVMojdBWS-JtH7TliWkVg)
