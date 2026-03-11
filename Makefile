gen:
	#mkdir -p assembly_output
	python3 main.py --template resource/riscv/template.S example.json --output_dir assembly_output

gen2:
	python3 main.py -t resource/riscv/template.S example.json -D assembly_output
	python3 main.py example.json -D assembly_output

compile-%:gen
	riscv-gcc template_%.S linker.ld -o target/template_%.elf
	riscv-objcopy target/template_%.elf target/template_%.hex
	riscv-objcopy target/template_%.elf target/template_%.bin
	riscv-objdump target/template_%.elf target/template_%.dump
#对target/目录进行搜索，所有target/template_*.S这样的文件名都被匹配到，然后解析出compile-%需要的目标名字
TARGET_LIST=$(...) #所有target/template_*.S这样的文件名都被匹配到，解析出"template_"后面的内容
COMPILE_TARGET_LIST=$(foreach ...) #把解析出来的内容拼接成"compile-xxx"的样子
run:$(COMPILE_TARGET_LIST)
.default=run