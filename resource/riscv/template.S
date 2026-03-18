#include "encoding.h"

.macro SET_CSR _csr, _t1, _VAL
    li \_t1, \_VAL
	csrw \_csr, \_t1
.endm

.macro SET_FPR _fpr, _t1, _VAL
    li \_t1, \_VAL
	fmv.w.x \_fpr, \_t1
.endm

.macro SET_PRV _t1, _PRV
    li \_t1, 0x1800
    csrc mstatus, \_t1
    li \_t1, (\_PRV << 11)
    csrs mstatus, \_t1
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

	#current_prv
	SET_PRV t1, ${cur_privilege}

	# FPRs: SET_FPR <fpr>, t1, ${<fpr>_VAL}
	SET_FPR f0, t1, ${F0_VAL}
	SET_FPR f1, t1, ${F1_VAL}
	SET_FPR f2, t1, ${F2_VAL}
	SET_FPR f3, t1, ${F3_VAL}
	SET_FPR f4, t1, ${F4_VAL}
	SET_FPR f5, t1, ${F5_VAL}
	SET_FPR f6, t1, ${F6_VAL}
	SET_FPR f7, t1, ${F7_VAL}
	SET_FPR f8, t1, ${F8_VAL}
	SET_FPR f9, t1, ${F9_VAL}
	SET_FPR f10, t1, ${F10_VAL}
	SET_FPR f11, t1, ${F11_VAL}
	SET_FPR f12, t1, ${F12_VAL}
	SET_FPR f13, t1, ${F13_VAL}
	SET_FPR f14, t1, ${F14_VAL}
	SET_FPR f15, t1, ${F15_VAL}
	SET_FPR f16, t1, ${F16_VAL}
	SET_FPR f17, t1, ${F17_VAL}
	SET_FPR f18, t1, ${F18_VAL}
	SET_FPR f19, t1, ${F19_VAL}
	SET_FPR f20, t1, ${F20_VAL}
	SET_FPR f21, t1, ${F21_VAL}
	SET_FPR f22, t1, ${F22_VAL}
	SET_FPR f23, t1, ${F23_VAL}
	SET_FPR f24, t1, ${F24_VAL}
	SET_FPR f25, t1, ${F25_VAL}
	SET_FPR f26, t1, ${F26_VAL}
	SET_FPR f27, t1, ${F27_VAL}
	SET_FPR f28, t1, ${F28_VAL}
	SET_FPR f29, t1, ${F29_VAL}
	SET_FPR f30, t1, ${F30_VAL}
	SET_FPR f31, t1, ${F31_VAL}
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

	${test_ins}
