# Assembly-Gen Makefile
# RISC-V 测试用例生成器和编译脚本

# 配置
PYTHON := python3
MAIN_SCRIPT := main.py
COMPILE_HELPER := compile_helper.py
DEFAULT_TEMPLATE := resource/riscv/template.S
DEFAULT_JSON := resource/example.json
OUTPUT_DIR := target
LINKER_SCRIPT := linker.ld

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
	@echo "  make compile-add   - 生成并编译 add 指令的测试用例"
	@echo "  make compile FILE=target/template_xxx.S - 编译单个文件"
	@echo "  make clean         - 清理生成的文件"
	@echo "  make test          - 运行所有测试"
	@echo "  make help          - 显示此帮助信息"
	@echo ""
	@echo "环境变量:"
	@echo "  ASSEMBLY_GEN_GCC   - 指定 GCC 命令（默认自动检测）"
	@echo "  ASSEMBLY_GEN_OBJCOPY - 指定 objcopy 命令"
	@echo "  ASSEMBLY_GEN_OBJDUMP - 指定 objdump 命令"
	@echo ""
	@echo "示例:"
	@echo "  make gen JSON=my_test.json"
	@echo "  make compile FILE=target/template_rv32d_add_x1_x1_x1.S"

# 检查工具链（静默模式，不打印任何消息）
.PHONY: check-tools
check-tools:
	@$(PYTHON) $(COMPILE_HELPER) --version >/dev/null 2>&1 || \
		(echo "错误: 未找到可用的 RISC-V 工具链" >&2; \
		 echo "请安装 RISC-V 工具链或确保 clang/llvm-objcopy/llvm-objdump 在 PATH 中" >&2; \
		 exit 1)

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

# 生成并编译 add 指令测试用例
.PHONY: compile-add
compile-add:
	@echo "生成并编译 add 指令测试用例..."
	@mkdir -p $(OUTPUT_DIR)
	@$(PYTHON) $(MAIN_SCRIPT) --template $(DEFAULT_TEMPLATE) $(DEFAULT_JSON) --output_dir $(OUTPUT_DIR) >/dev/null 2>&1 || \
		(echo "错误: 生成汇编文件失败" >&2; exit 1)
	@$(MAKE) --no-print-directory compile-single FILE=$(OUTPUT_DIR)/template_rv32d_add_x1_x1_x1.S XLEN=32

# 编译单个汇编文件
.PHONY: compile-single
compile-single: check-tools
	@if [ -z "$(FILE)" ]; then \
		echo "错误: 请指定 FILE 参数" >&2; \
		exit 1; \
	fi
	@if [ ! -f "$(FILE)" ]; then \
		echo "错误: 文件不存在: $(FILE)" >&2; \
		exit 1; \
	fi
	@echo "编译 $(FILE)..."
	@BASENAME=$$(basename $(FILE) .S); \
	XLEN=$${XLEN:-32}; \
	$(PYTHON) $(COMPILE_HELPER) "$(FILE)" -o "$(OUTPUT_DIR)/$$BASENAME" -x $$XLEN -e IMACFD -T $(LINKER_SCRIPT); \
	if [ $$? -eq 0 ]; then \
		echo "编译成功: $$BASENAME"; \
	else \
		echo "编译失败: $$BASENAME" >&2; \
		exit 1; \
	fi

# 编译单个汇编文件（用户调用接口）
.PHONY: compile
compile: check-tools
	@if [ -z "$(FILE)" ]; then \
		echo "错误: 请指定 FILE 参数，如: make compile FILE=target/template_xxx.S" >&2; \
		exit 1; \
	fi
	@if [ ! -f "$(FILE)" ]; then \
		echo "错误: 文件不存在: $(FILE)" >&2; \
		exit 1; \
	fi
	@echo "编译 $(FILE)..."
	@BASENAME=$$(basename $(FILE) .S); \
	FILENAME=$$(basename "$(FILE)"); \
	case "$$FILENAME" in \
		*rv32*|*32d*) XLEN=32 ;; \
		*rv64*|*64d*) XLEN=64 ;; \
		*) XLEN=32 ;; \
	esac; \
	$(PYTHON) $(COMPILE_HELPER) "$(FILE)" -o "$(OUTPUT_DIR)/$$BASENAME" -x $$XLEN -e IMACFD -T $(LINKER_SCRIPT); \
	if [ $$? -eq 0 ]; then \
		echo "编译成功: $$BASENAME"; \
	else \
		echo "编译失败: $$BASENAME" >&2; \
		exit 1; \
	fi

# 编译所有生成的汇编文件
.PHONY: compile-all
compile-all: check-tools
	@echo "编译所有生成的汇编文件..."
	@FOUND=0; \
	FAILED=0; \
	for file in $(OUTPUT_DIR)/template_*.S; do \
		if [ -f "$$file" ]; then \
			FOUND=1; \
			BASENAME=$$(basename "$$file" .S); \
			FILENAME=$$(basename "$$file"); \
			\
			# 从文件名推断 xlen \
			case "$$FILENAME" in \
				*rv32*|*32d*) XLEN=32 ;; \
				*rv64*|*64d*) XLEN=64 ;; \
				*) XLEN=32 ;; \
			esac; \
			\
			echo "编译 $$file..."; \
			$(PYTHON) $(COMPILE_HELPER) "$$file" -o "$(OUTPUT_DIR)/$$BASENAME" -x $$XLEN -e IMACFD -T $(LINKER_SCRIPT); \
			if [ $$? -ne 0 ]; then \
				echo "错误: 编译失败: $$BASENAME" >&2; \
				FAILED=1; \
			fi; \
		fi \
	done; \
	if [ $$FOUND -eq 0 ]; then \
		echo "错误: 未找到任何汇编文件" >&2; \
		exit 1; \
	fi; \
	if [ $$FAILED -eq 1 ]; then \
		echo "错误: 部分文件编译失败" >&2; \
		exit 1; \
	fi

# 生成并编译所有
.PHONY: run
run:
	@echo "生成汇编文件..."
	@mkdir -p $(OUTPUT_DIR)
	@$(PYTHON) $(MAIN_SCRIPT) --template $(DEFAULT_TEMPLATE) $(DEFAULT_JSON) --output_dir $(OUTPUT_DIR)
	@echo ""
	@echo "编译汇编文件..."
	@$(MAKE) --no-print-directory compile-all
	@if [ $$? -eq 0 ]; then \
		echo ""; \
		echo "完成!"; \
	else \
		echo ""; \
		echo "错误: 编译失败" >&2; \
		exit 1; \
	fi

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
	@ls -1 $(OUTPUT_DIR)/template_*.S 2>/dev/null || echo "  (无)"
	@echo ""
	@echo "生成的 ELF 文件:"
	@ls -1 $(OUTPUT_DIR)/template_*.elf 2>/dev/null || echo "  (无)"

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
