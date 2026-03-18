## Usage
```
python3 main.py --template resource/riscv/template.S example.json --output-dir assembly_output

python3 main.py -t resource/riscv/template.S example.json -o <assembly_output_dir>

# 根据json文件，确定架构riscv后，有默认路径resource/riscv/template.S
python3 main.py example.json -o <assembly_output_dir>
```