
.macro SET_CSR _csr, _t1, _VAL
    li \_t1, \_VAL
	csrw \_csr, \_t1
.endm

.macro SET_FPR _fpr, _t1, _VAL
    li \_t1, \_VAL
	fmv.w.x \_fpr, \_t1
.endm

 .section .text.init;
 .align  6;
 .weak stvec_handler;
 .weak mtvec_handler;
 .global _start;

_start:
	# CSRs: SET_CSR <csr>, t1, ${<csr>_VAL}
	SET_CSR mstatus, t1, ${MSTATUS_VAL}
	SET_CSR mepc, t1, ${MEPC_VAL}
	# FPRs: SET_FPR <fpr>, t1, ${<fpr>_VAL}
	flw f0, ${F0_VAL}(sp)
	flw f1, ${F1_VAL}(sp)
	flw f2, ${F2_VAL}(sp)
	flw f3, ${F3_VAL}(sp)
	flw f4, ${F4_VAL}(sp)
	flw f5, ${F5_VAL}(sp)
	flw f6, ${F6_VAL}(sp)
	flw f7, ${F7_VAL}(sp)
	flw f8, ${F8_VAL}(sp)
	flw f9, ${F9_VAL}(sp)
	flw f10, ${F10_VAL}(sp)
	flw f11, ${F11_VAL}(sp)
	flw f12, ${F12_VAL}(sp)
	flw f13, ${F13_VAL}(sp)
	flw f14, ${F14_VAL}(sp)
	flw f15, ${F15_VAL}(sp)
	flw f16, ${F16_VAL}(sp)
	flw f17, ${F17_VAL}(sp)
	flw f18, ${F18_VAL}(sp)
	flw f19, ${F19_VAL}(sp)
	flw f20, ${F20_VAL}(sp)
	flw f21, ${F21_VAL}(sp)
	flw f22, ${F22_VAL}(sp)
	flw f23, ${F23_VAL}(sp)
	flw f24, ${F24_VAL}(sp)
	flw f25, ${F25_VAL}(sp)
	flw f26, ${F26_VAL}(sp)
	flw f27, ${F27_VAL}(sp)
	flw f28, ${F28_VAL}(sp)
	flw f29, ${F29_VAL}(sp)
	flw f30, ${F30_VAL}(sp)
	flw f31, ${F31_VAL}(sp)
	# GPRs: li <gpr>, ${<gpr>_VAL}
	li x1, ${X1_VAL}
	li x2, ${X2_VAL}
	li x3, ${X3_VAL}
	li x4, ${X4_VAL}
	li x5, ${X5_VAL}
	li x6, ${X6_VAL}
	li x7, ${X7_VAL}
	li x8, ${X8_VAL}
	li x9, ${X9_VAL}
	li x10, ${X10_VAL}
	li x11, ${X11_VAL}
	li x12, ${X12_VAL}
	li x13, ${X13_VAL}
	li x14, ${X14_VAL}
	li x15, ${X15_VAL}
	li x16, ${X16_VAL}
	li x17, ${X17_VAL}
	li x18, ${X18_VAL}
	li x19, ${X19_VAL}
	li x20, ${X20_VAL}
	li x21, ${X21_VAL}
	li x22, ${X22_VAL}
	li x23, ${X23_VAL}
	li x24, ${X24_VAL}
	li x25, ${X25_VAL}
	li x26, ${X26_VAL}
	li x27, ${X27_VAL}
	li x28, ${X28_VAL}
	li x29, ${X29_VAL}
	li x30, ${X30_VAL}
	li x31, ${X31_VAL}
