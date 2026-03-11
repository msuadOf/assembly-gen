# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

并且，所有的输出和文件都是使用中文。

## 项目概述

这是 **isla-runner** 项目的 **assembly-gen** 子项目 —— 一个从 JSON 规范生成 RISC-V 汇编测试用例的框架。这些测试用例旨在与 Isla 符号执行引擎配合使用。

JSON 规范指定的isa-state通过文本替换template中的预设词$xxx，能快速构建一个完整的riscv上下文，用于给待测试指令提供一个指定上下文环境。

### isla-runner 项目背景

父项目汇集了以下兼容版本的工具：
- **sail** - 用于编写指令集架构规范的语言（基于 OCaml）
- **sail-riscv** - 用 Sail 编写的 RISC-V ISA 规范
- **isla** - 针对 Sail 规范的符号执行引擎（基于 Rust）

Isla 可以符号执行 Sail IR（中间表示）文件，并可以使用 Z3 等 SMT 求解器对公理化内存模型进行验证。

## assembly-gen 工作原理

此工具从 JSON 规范生成 RISC-V 汇编测试文件。核心机制是：**JSON 规范指定的 isa-state 通过文本替换 template 中的预设占位符 `${xxx}`，能快速构建一个完整的 RISC-V 上下文，用于给待测试指令提供一个指定上下文环境。**

JSON 规范包含：
- 架构配置（xlen：32/64，扩展：IMACFD 等）
- 要执行的测试指令
- 初始 ISA 状态（GPR 值、CSR 值）

生成的汇编可以在真实硬件或模拟器上编译和执行，结果可以与 Isla 的符号执行预测进行比较。

## 构建和测试命令

### 设置父项目依赖项（首次使用）

在父目录 `isla-runner/` 中：
```bash
# 克隆并构建 sail、sail-riscv 和 isla 仓库
make -j$(nproc) repos

# 这将会：
# 1. 克隆 sail@commit:446fb477 并通过 opam 安装
# 2. 克隆 isla 并构建 isla-sail
# 3. 克隆 sail-riscv，应用补丁，并生成 rv32d.ir 和 rv64d.ir（每个需要 8-10 分钟）
```

### 生成汇编

```bash
# 使用显式模板路径
python3 main.py --template resource/riscv/template.S example.json --output_dir assembly_output

# 使用短选项
python3 main.py -t resource/riscv/template.S example.json -D assembly_output

# 使用默认模板路径（从 arch: riscv 推断）
python3 main.py example.json -D assembly_output
```

### 编译生成的汇编

```bash
# 生成并编译特定的测试用例
make compile-<name>

# 生成并编译所有测试用例
make run
```

## 架构

### 输入 JSON 格式

JSON 输入文件包含测试用例规范数组：

```json
{
  "gen": [
    {
      "arch": {
        "pretty-name": "rv32d",
        "name": "riscv",
        "xlen": "32",
        "ext": "IMACFD"
      },
      "test-ins": "add x1,x1,x1",
      "isa-state": {
        "x1": "32'b00_01",
        "csrs": {
          "mstatus": "32'b0011_00xx_0000_0101",
          "mepc": "32'h80000000"
        }
      }
    }
  ]
}
```

### Python 代码结构（待实现）

该框架遵循以下架构（目前 `main.py` 中只有伪代码）：

```
Value 类：
  - 表示位向量值（例如 "64'b0010_0001"、"32'h80000000"）
  - parse()：解析二进制/十六进制字面量字符串
  - to_hex()：转换为十六进制字符串用于汇编输出

GenericTarget 类（基类）：
  - __init__(json, template_path)：从 JSON 规范初始化
  - get_arch()：返回架构信息
  - get_isa_state()：返回 ISA 状态字典
  - parse_template(template)：解析模板字符串（抽象）

RISCV 类（继承 GenericTarget）：
  - xlen：32 或 64
  - isa_state_table：GPR（x0-x31）和 CSR 名称列表
  - parse_template()：用 isa_state 中的值替换 ${register} 占位符
  - gen_assembly()：加载模板，解析它，返回完整的汇编
```

### 模板系统

模板系统是 assembly-gen 的核心机制。`resource/riscv/template.S` 中的汇编模板支持占位符，这些占位符会被 JSON 规范中的 `isa-state` 值替换：

**占位符格式：**
- `${x0}`、`${x1}`、...、`${x31}` - 通用寄存器
- `${mstatus}`、`${mepc}` 等 - 控制和状态寄存器

**替换规则：**
- 如果 `isa-state` 中提供了对应寄存器的值，则使用该值
- 缺失的值默认为 `0`
- 支持位向量字面量格式：`32'b0011_0101`（二进制）、`32'h80000000`（十六进制）

模板文件需要创建 —— 目前为空。

## 开发说明

### 当前状态

assembly-gen 框架 **尚未完成**，需要实现：
- `main.py` 仅包含伪代码注释
- `resource/riscv/template.S` 为空
- 没有实际的 Value 类实现用于位向量解析
- 没有 JSON 解析或 CLI 参数处理

### 实现优先级

1. **Value 类**：解析位向量字面量，如 `32'b0011_0101`、`64'hDEADBEEF`
2. **JSON 解析**：读取输入文件并提取测试用例规范
3. **模板解析**：实现占位符替换逻辑
4. **RISCV 类**：添加 GPR（x0-x31）和 CSR 定义
5. **CLI**：实现 argparse 处理 `-t`、`-D` 和位置参数
6. **模板文件**：创建带有适当指令的基本 RISC-V 汇编模板

### 相关文件

- `../rv32d.ir`、`../rv64d.ir` - 由 sail-riscv 生成的中间表示文件
- `../isla/isla-sail/isla-sail` - 使用 IR 文件进行符号执行的 CLI 工具
- `../sail-riscv/build/model/*.ir` - 为 RISC-V 变体生成的 IR 文件

### Isla 集成

生成汇编测试用例后，可以使用 Isla 进行验证：

```bash
# 在 isla/ 目录中
cargo run --bin isarch --release -- -A ../rv32d.ir -C configs/riscv32.toml list-instructions
cargo run --bin isarch --release -- -A ../rv32d.ir -C configs/riscv32.toml solve-state <instruction>
```

有关 Isla 符号执行引擎的更多信息，请参阅 `../isla/CLAUDE.md`。

## 文件结构

```
assembly-gen/
├── main.py              # 主入口点（未完成 - 仅伪代码）
│                        # 包含 Value、GenericTarget、RISCV 类
├── Makefile             # 构建和编译目标
├── README.md            # 使用文档
├── CLAUDE.md            # 此文件
└── resource/
    ├── example.json     # 示例输入规范
    └── riscv/
        └── template.S   # RISC-V 汇编模板（空，需要创建）
```
