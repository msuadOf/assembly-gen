# Assembly-Gen Makefile
# RISC-V 测试用例生成器和编译脚本

# 配置
PYTHON := python3
MAIN_SCRIPT := main.py
DEFAULT_TEMPLATE := resource/riscv/template.S
DEFAULT_JSON := resource/example.json
OUTPUT_DIR := target

# RISC-V 工具链
RISCV_GCC := riscv-gcc
RISCV_OBJCOPY := riscv-objcopy
RISCV_OBJDUMP := riscv-objdump

# 编译选项
ARCH_FLAGS := -march=rv32imac -mabi=ilp32
LINKER_SCRIPT := linker.ld
GCC_FLAGS := -nostartfiles -T $(LINKER_SCRIPT)

# 默认目标
.DEFAULT_GOAL := run

# 帮助目标
.PHONY: help
help:
	@echo "Assembly-Gen Makefile"
	@echo ""
	@echo "可用目标:"
	@echo "  make run           - 生成所有汇编文件并编译"
	@echo "  make gen           - 生成所有汇编文件"
	@echo "  make compile-all   - 编译所有生成的汇编文件"
	@echo "  make clean         - 清理生成的文件"
	@echo "  make test          - 运行所有测试"
	@echo "  make help          - 显示此帮助信息"
	@echo ""
	@echo "示例:"
	@echo "  make gen JSON=my_test.json"
	@echo "  make compile FILE=target/template_rv32d_add_x1_x1_x1.S"

# 检查 RISC-V 工具链
.PHONY: check-tools
check-tools:
	@command -v $(RISCV_GCC) >/dev/null 2>&1 || \
		(echo "警告: 未找到 RISC-V 工具链 ($(RISCV_GCC))"; \
		 echo "编译目标将被跳过")

# 生成汇编文件
.PHONY: gen
gen:
	@echo "生成汇编文件..."
	@mkdir -p $(OUTPUT_DIR)
	$(PYTHON) $(MAIN_SCRIPT) --template $(DEFAULT_TEMPLATE) $(DEFAULT_JSON) --output_dir $(OUTPUT_DIR)

# 使用自定义 JSON 文件生成
.PHONY: gen-custom
gen-custom:
	@echo "生成汇编文件 (自定义 JSON: $(JSON))..."
	@mkdir -p $(OUTPUT_DIR)
	$(PYTHON) $(MAIN_SCRIPT) --template $(DEFAULT_TEMPLATE) $(JSON) --output_dir $(OUTPUT_DIR)

# 编译单个汇编文件
# 用法: make compile FILE=target/template_xxx.S
.PHONY: compile
compile: check-tools
	@if [ -z "$(FILE)" ]; then \
		echo "错误: 请指定 FILE 参数，如: make compile FILE=target/template_xxx.S"; \
		exit 1; \
	fi
	@if [ ! -f "$(FILE)" ]; then \
		echo "错误: 文件不存在: $(FILE)"; \
		exit 1; \
	fi
	@echo "编译 $(FILE)..."
	@BASENAME=$$(basename $(FILE) .S); \
	ELF_FILE=$(OUTPUT_DIR)/$$BASENAME.elf; \
	HEX_FILE=$(OUTPUT_DIR)/$$BASENAME.hex; \
	BIN_FILE=$(OUTPUT_DIR)/$$BASENAME.bin; \
	DUMP_FILE=$(OUTPUT_DIR)/$$BASENAME.dump; \
	$(RISCV_GCC) $(GCC_FLAGS) $(FILE) -o $$ELF_FILE && \
	$(RISCV_OBJCOPY) -O ihex $$ELF_FILE $$HEX_FILE && \
	$(RISCV_OBJCOPY) -O binary $$ELF_FILE $$BIN_FILE && \
	$(RISCV_OBJDUMP) -d $$ELF_FILE > $$DUMP_FILE && \
	echo "编译成功: $$BASENAME"

# 编译所有生成的汇编文件
.PHONY: compile-all
compile-all: check-tools
	@echo "编译所有生成的汇编文件..."
	@if command -v $(RISCV_GCC) >/dev/null 2>&1; then \
		for file in $(OUTPUT_DIR)/template_*.S; do \
			if [ -f "$$file" ]; then \
				echo "编译 $$file..."; \
				BASENAME=$$(basename "$$file" .S); \
				ELF_FILE=$(OUTPUT_DIR)/$$BASENAME.elf; \
				HEX_FILE=$(OUTPUT_DIR)/$$BASENAME.hex; \
				BIN_FILE=$(OUTPUT_DIR)/$$BASENAME.bin; \
				DUMP_FILE=$(OUTPUT_DIR)/$$BASENAME.dump; \
				$(RISCV_GCC) $(GCC_FLAGS) "$$file" -o $$ELF_FILE && \
				$(RISCV_OBJCOPY) -O ihex $$ELF_FILE $$HEX_FILE && \
				$(RISCV_OBJCOPY) -O binary $$ELF_FILE $$BIN_FILE && \
				$(RISCV_OBJDUMP) -d $$ELF_FILE > $$DUMP_FILE || \
				echo "警告: 编译失败: $$BASENAME"; \
			fi \
		done; \
		echo "编译完成"; \
	else \
		echo "跳过编译: RISC-V 工具链未找到"; \
	fi

# 生成并编译所有
.PHONY: run
run: gen compile-all

# 清理生成的文件
.PHONY: clean
clean:
	@echo "清理生成的文件..."
	@rm -rf $(OUTPUT_DIR)
	@echo "清理完成"

# 显示生成的文件
.PHONY: list
list:
	@echo "生成的汇编文件:"
	@ls -1 $(OUTPUT_DIR)/template_*.S 2>/dev/null || echo "无"
	@echo ""
	@echo "生成的 ELF 文件:"
	@ls -1 $(OUTPUT_DIR)/template_*.elf 2>/dev/null || echo "无"

# 运行所有测试
.PHONY: test
test:
	@echo "运行测试..."
	$(PYTHON) tests/test_all.py

# 快速验证测试
.PHONY: test-quick
test-quick:
	@echo "快速验证..."
	@$(PYTHON) -c "import sys; sys.path.insert(0, '.'); from main import Value; v = Value('32\\'b0011_0101'); print(f'Value test: {v.to_hex()} == 0x00000035')"
	@$(PYTHON) -c "import sys; sys.path.insert(0, '.'); from main import load_json_spec; data = load_json_spec('resource/example.json'); print(f'JSON test: loaded {len(data[\"gen\"])} test cases')"
	@echo "快速验证通过"
