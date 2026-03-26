gen:
	rm -rf assembly_output && python3 main.py --template resource/riscv/template.S --json-dir input/ --output-dir assembly_output

SRC = $(wildcard assembly_output/*.S)
BUILD_DIR = build

ELF = $(patsubst assembly_output/%.S,$(BUILD_DIR)/%.elf,$(SRC))
BIN = $(patsubst assembly_output/%.S,$(BUILD_DIR)/%.bin,$(SRC))
HEX = $(patsubst assembly_output/%.S,$(BUILD_DIR)/%.hex,$(SRC))
DIS = $(patsubst assembly_output/%.S,$(BUILD_DIR)/%.dis,$(SRC))
ASM = $(patsubst assembly_output/%.S,$(BUILD_DIR)/%.asm,$(SRC))
DUMP = $(patsubst assembly_output/%.S,$(BUILD_DIR)/%.dump,$(SRC))
MAP = $(patsubst assembly_output/%.S,$(BUILD_DIR)/%.map,$(SRC))

VPATH = assembly_output

include resource/riscv/scripts/compile.mk
# commands
env:
	python3 -m venv venv
	source venv/bin/activate && pip install -r requirements.txt

test:
	python -m pytest -v

run:$(COMPILE_TARGET_LIST)
.default=run