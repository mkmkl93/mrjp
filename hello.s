.globl _start
_start:
    mov    $message, %rdi
#    mov    $0, %edi    # Yes, it does work with input = 0
    call   print_string

    mov     $123123, %rdi
    call    print_int

    xor    %edi, %edi
    mov    $60, %eax
    syscall                             # sys_exit(0)

message:
        .ascii  "Hello, world\n"
