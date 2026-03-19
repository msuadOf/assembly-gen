/* RISC-V 链接脚本 */
OUTPUT_ARCH("riscv")
ENTRY(_start)

/* 内存区域定义 */
MEMORY
{
    /* 可根据实际硬件调整地址 */
    RAM (rwx) : ORIGIN = 0x80000000, LENGTH = 128M
}

/* 段定义 */
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

    /* 读写数据段 */
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

    /* 丢弃不需要的段 */
    /DISCARD/ : {
        *(.comment)
        *(.note*)
        *(.eh_frame*)
        *(.gnu.debuglink)
        *(.gnu.attributes)
        *(.ARM.attributes)
        *(.riscv.attributes)
    }
}
