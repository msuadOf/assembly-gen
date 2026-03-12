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
    # ${sp_save_comment}
    # ${sp_save_instruction}
    ${sp_save_move}

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
${gpr_init_x16_x31}
    # ${x30_comment}
${x31_init}

    # === CSR 初始化 ===
    # ${csr_scratch_comment}
    # ${csr_scratch_save}
    ${csr_init_mstatus}
    ${csr_init_mepc}
    # ${csr_scratch_restore}

    # 恢复原始栈指针
    ${sp_restore_move}

    # === 设置 x2 (sp) ===
    # 在所有栈操作完成后设置 x2，确保测试指令执行时 x2 有正确的值
    li x2, ${x2}

    # === 设置 x30 (t5) ===
    # ${x30_restore_comment}
    ${x30_restore_instruction}

    # === 测试指令 ===
    ${test_ins}

    # === 结束标记 ===
    nop
    nop

    # 退出（使用 ecall）
    li a0, 0
    ecall
