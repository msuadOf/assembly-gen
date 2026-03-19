# RISC-V 裸机汇编编译 Makefile
TOOL_DIR := $(realpath $(dir $(lastword $(MAKEFILE_LIST)))..)

# 工具链
CROSS_COMPILE = riscv64-linux-gnu-
CC = $(CROSS_COMPILE)gcc
AS = $(CROSS_COMPILE)gcc
LD = $(CROSS_COMPILE)ld
OBJCOPY = $(CROSS_COMPILE)objcopy
OBJDUMP = $(CROSS_COMPILE)objdump

# 架构和 ABI 配置
# MARCH ?= rv64imafdc
# MABI ?= lp64d
MARCH ?= rv32imafdc_zicsr
MABI ?= ilp32d

# 编译/汇编选项
INC_PATH = $(TOOL_DIR)/include
INCFLAGS = $(addprefix -I, $(INC_PATH))

COMMON_CFLAGS := -fno-pic -march=$(MARCH) -mabi=$(MABI) -mcmodel=medany -mstrict-align
CFLAGS = $(COMMON_CFLAGS) -static -fno-asynchronous-unwind-tables -fno-builtin -fno-stack-protector -Wno-main -fdata-sections -ffunction-sections
ASFLAGS = $(COMMON_CFLAGS) \
	$(INCFLAGS) \
	-O0

# 链接脚本
LD_SCRIPT = $(TOOL_DIR)/scripts/link.ld

# 链接选项（不含 Map，Map 在模式规则中单独处理）
LDFLAGS = -melf32lriscv \
	-nostdlib \
	-static \
	-T $(LD_SCRIPT) \
	-e _start \
	--gc-sections \
	-z noexecstack \
	$(NULL)

# objcopy 选项
OBCOPY_FLAGS = -O binary

# 默认编译目标
compile: $(BUILD_DIR) $(BIN) $(HEX) $(DIS) $(ASM) $(DUMP)

# 创建构建目录
$(BUILD_DIR):
	@mkdir -p $@

# ============================================================
# 通用构建规则
# ============================================================

# 模式规则：从汇编源文件生成目标文件
$(BUILD_DIR)/%.o: %.S | $(BUILD_DIR)
	@echo "  AS      $@"
	$(AS) $(ASFLAGS) -c -o $@ $<

# 模式规则：从目标文件生成 ELF 文件
$(BUILD_DIR)/%.elf: $(BUILD_DIR)/%.o
	@echo "  LD      $@"
	$(LD) $(LDFLAGS) -o $@ --start-group $^ --end-group

# 兼容性规则：当 $(SRC) 是单个文件时
ifneq ($(SRC),)
# 提取目标文件名（不含扩展名）
TARGET_BASE = $(basename $(SRC))

# ELF 文件生成规则
# $(ELF): $(SRC) | $(BUILD_DIR)
# 	$(CC) $(ASFLAGS) $(LDFLAGS) -o $@ $^

# 通用输出格式生成规则（基于 ELF）
$(BUILD_DIR)/%.bin: $(BUILD_DIR)/%.elf
	@echo "  OBJCOPY $@"
	@$(OBJCOPY) $(OBCOPY_FLAGS) $< $@

$(BUILD_DIR)/%.hex: $(BUILD_DIR)/%.elf
	@echo "  OBJCOPY $@"
	@$(OBJCOPY) -O ihex $< $@

$(BUILD_DIR)/%.dis: $(BUILD_DIR)/%.elf
	@echo "  OBJDUMP $@"
	@$(OBJDUMP) -d -S $< > $@

$(BUILD_DIR)/%.asm: $(BUILD_DIR)/%.elf
	@echo "  OBJDUMP $@"
	@$(OBJDUMP) -d -S -r $< > $@

$(BUILD_DIR)/%.dump: $(BUILD_DIR)/%.elf
	@echo "  OBJDUMP $@"
	@$(OBJDUMP) -s -D $< > $@
endif
