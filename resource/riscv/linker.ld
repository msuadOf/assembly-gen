/* RISC-V 裸机链接脚本 */

OUTPUT_ARCH("riscv")
ENTRY(_start)

MEMORY
{
    /* 定义内存区域，从 0x80000000 开始，大小为 128MB */
    RAM (rwxai) : ORIGIN = 0x80000000, LENGTH = 128M
}

SECTIONS
{
    /* 代码段 */
    .text : {
        *(.text.init)
        *(.text*)
    } > RAM

    /* 只读数据段 */
    .rodata : {
        *(.rodata*)
    } > RAM

    /* 数据段 */
    .data : {
        *(.data*)
    } > RAM

    /* 未初始化数据段 */
    .bss : {
        __bss_start = .;
        *(.bss*)
        *(COMMON)
        __bss_end = .;
    } > RAM

    /* 栈段（预留空间） */
    .stack : {
        __stack_start = .;
        . = . + 0x1000;  /* 4KB 栈空间 */
        __stack_end = .;
    } > RAM
}
