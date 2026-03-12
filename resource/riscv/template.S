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
    # ${x8_init}
${x8_init}
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
    # 保存 scratch 寄存器到栈
    ${scratch_reg_save}

    # 初始化各个 CSR（占位符由 Python 替换为实际值）
    li ${scratch_reg}, ${mstatus}
    csrw mstatus, ${scratch_reg}

    li ${scratch_reg}, ${mepc}
    csrw mepc, ${scratch_reg}

    # 其他 CSR 初始化（如果 JSON 中指定了值，则初始化）
    # 注意：即使 JSON 中未指定，这些 CSR 也会被初始化为默认值 0x00000000
    li ${scratch_reg}, ${mtvec}
    csrw mtvec, ${scratch_reg}

    li ${scratch_reg}, ${mcause}
    csrw mcause, ${scratch_reg}

    li ${scratch_reg}, ${mtval}
    csrw mtval, ${scratch_reg}

    li ${scratch_reg}, ${mip}
    csrw mip, ${scratch_reg}

    li ${scratch_reg}, ${mie}
    csrw mie, ${scratch_reg}

    # 注意：satp 只在 S-mode 中存在，M-mode 核心写入会引发非法指令陷阱
    # 如果需要 S-mode 支持，请取消下面的注释
    # li ${scratch_reg}, ${satp}
    # csrw satp, ${scratch_reg}

    # 恢复 scratch 寄存器
    ${scratch_reg_restore}

    # 恢复原始栈指针
    ${sp_restore_move}

    # === 恢复用于保存 sp 的寄存器 ===
    # ${x8_restore_comment}
    ${x8_restore_instruction}

    # === 设置 x2 (sp) ===
    # 在所有栈操作完成后设置 x2，确保测试指令执行时 x2 有正确的值
    li x2, ${x2}

    # === 设置 x30 (t5) ===
    # ${x30_restore_comment}
    ${x30_restore_instruction}

    # === 测试指令 ===
    ${test_ins}

    # === 结束标记 ===
    # 使用无限循环终止程序（避免 ecall 依赖 mtvec）
    # 对于模拟器/仿真器，可以检测到此循环并停止执行
    infinite_loop:
        j infinite_loop
