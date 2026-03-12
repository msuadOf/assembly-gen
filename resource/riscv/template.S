# RISC-V 测试用例模板
# 自动生成于: ${pretty_name}
# 架构: RISC-V (xlen=${xlen}, ext=${ext})
# 测试指令: ${test_ins}

.section .bss
.align 4
.stack_frame:
    .skip 64  # 预留 64 字节作为临时栈区域

.section .text
.globl _start

_start:
    # === 保存原始栈指针 ===
    # 使用 x30 (t5) 作为临时寄存器保存 sp
    # 然后设置一个安全的栈区域用于 CSR 初始化
    mv t5, sp
    la sp, .stack_frame + 60  # 指向栈区域顶部

    # === GPR 初始化 ===
    # 注意：x2 (sp) 在 CSR 初始化后设置，避免覆盖安全栈指针
    li x1, ${x1}
    li x3, ${x3}
    li x4, ${x4}
    li x5, ${x5}
    li x6, ${x6}
    li x7, ${x7}
    li x8, ${x8}
    li x9, ${x9}
    li x10, ${x10}
    li x11, ${x11}
    li x12, ${x12}
    li x13, ${x13}
    li x14, ${x14}
    li x15, ${x15}
    li x16, ${x16}
    li x17, ${x17}
    li x18, ${x18}
    li x19, ${x19}
    li x20, ${x20}
    li x21, ${x21}
    li x22, ${x22}
    li x23, ${x23}
    li x24, ${x24}
    li x25, ${x25}
    li x26, ${x26}
    li x27, ${x27}
    li x28, ${x28}
    li x29, ${x29}
    # x30 (t5) 保存了原始 sp，稍后恢复
    li x31, ${x31}

    # === CSR 初始化 ===
    # 使用 x31 (t6) 作为临时寄存器设置 CSR
    # 先保存 x31 的用户值到栈，使用后再恢复
    ${stack_store} t6, -${xlen_bytes}(sp)

    li t6, ${mstatus}
    csrw mstatus, t6

    li t6, ${mepc}
    csrw mepc, t6

    # 恢复 x31 的用户值
    ${stack_load} t6, -${xlen_bytes}(sp)

    # 恢复原始栈指针
    mv sp, t5

    # === 设置 x2 (sp) ===
    # 在所有栈操作完成后设置 x2，确保测试指令执行时 x2 有正确的值
    li x2, ${x2}

    # === 测试指令 ===
    ${test_ins}

    # === 结束标记 ===
    nop
    nop

    # 退出（使用 ecall）
    li a0, 0
    ecall
