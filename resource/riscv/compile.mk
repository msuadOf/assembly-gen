# RISC-V 裸机汇编编译 Makefile

# 工具链
CROSS_COMPILE = riscv64-linux-gnu-
CC = $(CROSS_COMPILE)gcc
AS = $(CROSS_COMPILE)as
LD = $(CROSS_COMPILE)ld
OBJCOPY = $(CROSS_COMPILE)objcopy
OBJDUMP = $(CROSS_COMPILE)objdump

# 架构和 ABI 配置
MARCH ?= rv64imac
MABI ?= lp64

# 编译/汇编选项
ASFLAGS = -march=$(MARCH) -mabi=$(MABI) \
	$(NULL)

# 链接选项
LDFLAGS = -march=$(MARCH) -mabi=$(MABI) \
	-nostdlib \
	-static \
	-Wl,--build-id=none \
	-Wl,-Ttext=0x80000000 \
	-Wl,-Map,$(MAP) \
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
	$(CC) $(ASFLAGS) -c -o $@ $<

# 模式规则：从目标文件生成 ELF 文件
$(BUILD_DIR)/%.elf: $(BUILD_DIR)/%.o
	$(CC) $(ASFLAGS) $(LDFLAGS) -o $@ $^

# 兼容性规则：当 $(SRC) 是单个文件时
ifneq ($(SRC),)
# 提取目标文件名（不含扩展名）
TARGET_BASE = $(basename $(SRC))

# ELF 文件生成规则
$(ELF): $(SRC) | $(BUILD_DIR)
	$(CC) $(ASFLAGS) $(LDFLAGS) -o $@ $^

# 通用输出格式生成规则（基于 ELF）
$(BUILD_DIR)/%.bin: $(BUILD_DIR)/%.elf
	$(OBJCOPY) $(OBCOPY_FLAGS) $< $@

$(BUILD_DIR)/%.hex: $(BUILD_DIR)/%.elf
	$(OBJCOPY) -O ihex $< $@

$(BUILD_DIR)/%.dis: $(BUILD_DIR)/%.elf
	$(OBJDUMP) -d -S $< > $@

$(BUILD_DIR)/%.asm: $(BUILD_DIR)/%.elf
	$(OBJDUMP) -d -S -r $< > $@

$(BUILD_DIR)/%.dump: $(BUILD_DIR)/%.elf
	$(OBJDUMP) -s -D $< > $@
endif