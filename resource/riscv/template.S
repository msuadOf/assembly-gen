# RISC-V 测试用例模板
# 自动生成于: ${pretty_name}
# 架构: RISC-V (xlen=${xlen}, ext=${ext})
# 测试指令: ${test_ins}

.section .text
.globl _start

_start:
    # === GPR 初始化 ===
    li x1, ${x1}
    li x2, ${x2}
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
    li x30, ${x30}
    li x31, ${x31}

    # === CSR 初始化 ===
    # 使用临时寄存器 t0 (x5) 设置 CSR
    li t0, ${mstatus}
    csrw mstatus, t0

    li t0, ${mepc}
    csrw mepc, t0

    # === 测试指令 ===
    ${test_ins}

    # === 结束标记 ===
    nop
    nop

    # 退出（使用 ecall）
    li a0, 0
    ecall
