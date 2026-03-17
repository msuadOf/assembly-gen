
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
	${CSRs}
	# FPRs: SET_FPR <fpr>, t1, ${<fpr>_VAL}
	${FPRs}
	# GPRs: li <gpr>, ${<gpr>_VAL}
	${GPRs}
