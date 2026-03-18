# 源文件和输出

# 手写模板转换配置
TEMPLATE_HANDWRITTEN = template_handwritten.S
TEMPLATE = template.S
TEMPLATE_HANDWRITTEN_CONVERTOR = convert_handwritten.py

# 从手写模板生成标准模板
gen_template: $(TEMPLATE)

$(TEMPLATE): $(TEMPLATE_HANDWRITTEN) $(TEMPLATE_HANDWRITTEN_CONVERTOR)
	@python3 $(TEMPLATE_HANDWRITTEN_CONVERTOR) --template $< --output $@
	@echo "转换: $< -> $@"

# ======编译=====
SRC = $(TEMPLATE) #template.S
BUILD_DIR = build
ELF = $(BUILD_DIR)/template.elf
BIN = $(BUILD_DIR)/template.bin
HEX = $(BUILD_DIR)/template.hex
DIS = $(BUILD_DIR)/template.dis
ASM = $(BUILD_DIR)/template.asm
DUMP = $(BUILD_DIR)/template.dump
MAP = $(BUILD_DIR)/template.map

-include scripts/compile.mk

# 清理
clean:
	rm -rf $(BUILD_DIR)

# 查看反汇编
dump: $(DIS)
	@cat $(DIS)

# 查看符号表
syms: $(ELF)
	@$(OBJDUMP) -t $<

.PHONY: all clean dump syms
