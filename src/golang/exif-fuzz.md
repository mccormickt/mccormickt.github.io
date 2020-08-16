# Exif Parser Fuzzing
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
---

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
---

## Input File Mutation

###The Bit Flip
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
---

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
---



