.globl printInt, printString
.p2align 4

# .globl print_integer            #void print_uint64(uint64_t value)
printInt:
    lea   -1(%rsp), %rsi        # We use the 128B red-zone as a buffer to hold the string
                                # a 64-bit integer is at most 20 digits long in base 10, so it fits.

    cmp     $0, %rdi            # Check if argument is negative
    jge     .neg_false
.neg_true:
    mov     $1, %r9             # Remember than argument was less than zero
    neg     %edi                # Negate the number and solve for positive
    jmp     .neg_end
.neg_false:
    mov     $0, %r9             # Remember than arguments is non negative
.neg_end:

    movb  $'\n', (%rsi)         # store the trailing newline byte.  (Right below the return address).
    # If you need a null-terminated string, leave an extra byte of room and store '\n\0'.  Or  push $'\n'

    mov    $10, %ecx            # same as  mov $10, %rcx  but 2 bytes shorter
    # note that newline (\n) has ASCII code 10, so we could actually have stored the newline with  movb %cl, (%rsi) to save code size.

    mov    %rdi, %rax           # function arg arrives in RDI; we need it in RAX for div
.Ltoascii_digit:                # do{
    xor    %edx, %edx
    div    %rcx                  #  rax = rdx:rax / 10.  rdx = remainder
                                 # store digits in MSD-first printing order, working backwards from the end of the string
    add    $'0', %edx            # integer to ASCII.  %dl would work, too, since we know this is 0-9
    dec    %rsi
    mov    %dl, (%rsi)           # *--p = (value%10) + '0';

    test   %rax, %rax
    jnz  .Ltoascii_digit        # } while(value != 0)

    cmp    $1, %r9             # If the number was negative then we must add '-'
    jne .add_sign_end
    dec    %rsi
    movb   $45, (%rsi)          # *--p = '-'
.add_sign_end:

    # If we used a loop-counter to print a fixed number of digits, we would get leading zeros
    # The do{}while() loop structure means the loop runs at least once, so we get "0\n" for input=0

    # Then print the whole string with one system call
    mov   $1, %eax              # call number from asm/unistd_64.h
    mov   $1, %edi              # fd=1
    # %rsi = start of the buffer
    mov   %rsp, %rdx
    sub   %rsi, %rdx            # length = one_past_end - start
    syscall                     # write(fd=1 /*rdi*/, buf /*rsi*/, length /*rdx*/); 64-bit ABI
    # rax = return value (or -errno)
    # rcx and r11 = garbage (destroyed by syscall/sysret)
    # all other registers = unmodified (saved/restored by the kernel)

    # we don't need to restore any registers, and we didn't modify RSP.
    ret

printString:
     mov  %rdi, %rbx
Again:
     mov   $1, %eax
     mov   $1, %edi
     mov   %rbx, %rsi
     mov   $1, %rdx
     syscall

     inc  %rbx
     cmp  $0, (%rbx)
     jne  Again

     ret
