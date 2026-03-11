/* RISC-V 链接器脚本 */
/* 用于 Assembly-Gen 生成的测试程序 */

ENTRY(_start)

MEMORY
{
    /* 定义内存区域 */
    RAM (rwx) : ORIGIN = 0x80000000, LENGTH = 16K
}

SECTIONS
{
    /* 代码段 */
    .text : {
        *(.text)
        *(.text.*)
    } > RAM

    /* 只读数据段 */
    .rodata : {
        *(.rodata)
        *(.rodata.*)
    } > RAM

    /* 数据段 */
    .data : {
        *(.data)
        *(.data.*)
    } > RAM

    /* 未初始化数据段 */
    .bss : {
        *(.bss)
        *(.bss.*)
        *(COMMON)
    } > RAM

    /* 堆栈段 */
    .stack : {
        . = ALIGN(16);
        . = . + 0x400; /* 1KB 堆栈 */
    } > RAM
}
