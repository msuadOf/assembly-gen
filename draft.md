# Assembly-Gen 实现草稿

## 1. 项目概述

### 1.1 项目目标

**assembly-gen** 旨在实现一个从 JSON 规范的上下文状态生成 RISC-V 汇编测试用例的框架。

### 1.2 核心机制

**模板驱动的文本替换系统**：JSON 规范指定的 `isa-state` 通过文本替换 template 中的预设占位符 `${xxx}`，快速构建一个完整的 RISC-V 上下文，为待测试指令提供指定的执行环境。


## 2. 技术架构设计

### 2.2 核心类设计

#### 2.2.1 Value 类

表示位向量值，支持多种格式的输入和转换。

```python
class Value:
    """
    表示位向量值（例如 "64'b0010_0001"、"32'h80000000"）

    属性:
        bits (int): 位宽
        value (int): 实际数值（无符号）
		mask (int): 置1的那一位为有效位，置0的为无效位（TODO: 无效位在做替换的时候支持只做有效位的指定，无效位保持原样）

    方法:
        __init__(exp: str): 从字符串解析位向量
        to_hex() -> str: 转换为十六进制字符串
        to_bin() -> str: 转换为二进制字符串
        to_dec() -> str: 返回整数值字符串
		to_num() -> int: 返回整数值
    """

    支持的格式:
        - 二进制: "32'b0011_0101"、"8'b101"
        - 十六进制: "32'h80000000"、"8'hFF"
        - 未知位 (x): "32'b0011_00xx_0000_0101"
```

#### 2.2.2 GenericTarget 类

所有架构目标的基类，定义通用接口。

```python
class GenericTarget:
    """
    架构目标基类

    属性:
        json (dict): 原始 JSON 规范
        arch (dict): 架构配置信息
        isa_state (dict): ISA 状态
        test_ins (str): 测试指令
        template_path (str): 模板文件路径

    方法:
        get_arch() -> dict: 返回架构信息
        get_isa_state() -> dict: 返回 ISA 状态
        parse_template(template: str) -> str: 解析模板（抽象方法）
        gen_assembly() -> str: 生成完整汇编代码
    """
```

#### 2.2.3 RISCV 类

RISC-V 架构的具体实现。

```python
class RISCV(GenericTarget):
    """
    RISC-V 架构实现

    属性:
        xlen (int): 32 或 64
        ext (str): 扩展集 (如 "IMACFD")
        isa_state_table (list): GPR 和 CSR 名称列表

    方法:
        parse_template(template: str) -> str:
            用 isa_state 中的值替换 ${register} 占位符
            缺失的值默认为 0

        gen_assembly() -> str:
            加载模板，解析它，返回完整的汇编
    """

    GPR 列表: x0, x1, ..., x31
    CSR 列表: mstatus, mepc, mtvec, mcause, ...
```

### 2.3 模板系统

#### 2.3.1 占位符格式

模板支持以下占位符：

| 占位符类型 | 格式 | 示例 | 说明 |
|-----------|------|------|------|
| 通用寄存器 | `${x0}` - `${x31}` | `${x1}`, `${x31}` | 32 个通用寄存器 |
| 控制状态寄存器 | `${csr_name}` | `${mstatus}`, `${mepc}` | 各种 CSR 寄存器 |
| 测试指令 | `${test_ins}` | `add x1,x1,x1` | 要测试的指令 |

#### 2.3.2 替换规则

1. 如果 `isa-state` 中提供了对应寄存器的值，则使用该值
2. 缺失的值默认为 `0`
3. 支持位向量字面量格式：
   - 二进制: `32'b0011_0101`
   - 十六进制: `32'h80000000`
   - 带未知位: `32'b0011_00xx_0000_0101`

---

## 3. 输入/输出格式

### 3.1 输入 JSON 格式

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

#### 字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `gen` | Array | 是 | 测试用例规范数组 |
| `arch.pretty-name` | String | 否 | 一个便于阅读架构名称 (rv32d, rv64d 等) |
| `arch.name` | String | 是 | 架构类型 (riscv) |
| `arch.xlen` | String | 是 | 位宽 (32 或 64) |
| `arch.ext` | String | 是 | 扩展集 (IMACFD 等) |
| `test-ins` | String | 是 | 要测试的指令 |
| `isa-state` | Object | 是 | 初始 ISA 状态 |
| `isa-state.csrs` | Object | 否 | CSR 寄存器值 |

### 3.2 输出汇编格式

生成的汇编文件应包含：

1. **头部信息**：架构、测试指令等元数据
2. **初始化代码**：设置 GPR 和 CSR 的值
3. **测试指令**：要测试的指令
4. **结束标记**：便于识别测试结束

示例输出结构：

```assembly
# Test case: add x1,x1,x1
# Architecture: rv32d (xlen=32, ext=IMACFD)

.section .text
.globl _start

_start:
    # 初始化 GPR
    li x1, 0x00000001

    # 初始化 CSR
    li t0, 0x05000030
    csrw mstatus, t0
    li t0, 0x80000000
    csrw mepc, t0

    # 测试指令
    add x1, x1, x1

    # 结束标记
    nop
    nop
	li a0,0
	ecall
```

---

## 4. 实现计划

### 4.1 实现优先级

#### 阶段 1：核心基础（高优先级）

1. **Value 类实现**
   - 解析二进制字面量 (`32'b0010_0001`)
   - 解析十六进制字面量 (`32'hDEADBEEF`)
   - 支持未知位 (`x`) 处理
   - 实现 `to_hex()` 方法

2. **JSON 解析**
   - 读取输入文件
   - 验证 JSON 格式
   - 提取测试用例规范

3. **CLI 参数处理**
   - `--template` / `-t`: 模板路径
   - `--output_dir` / `-D`: 输出目录
   - 位置参数: JSON 文件路径

#### 阶段 2：模板系统（中优先级）

4. **GenericTarget 基类**
   - 定义通用接口
   - 实现 `__init__` 方法
   - 实现 `get_arch()` 和 `get_isa_state()`

5. **RISCV 类实现**
   - 添加 GPR 列表 (x0-x31)
   - 添加 CSR 列表
   - 实现 `parse_template()` 占位符替换
   - 实现 `gen_assembly()` 模板加载

6. **模板文件创建**
   - 创建 `resource/riscv/template.S`
   - 定义基本结构和占位符

7. **生成指定名称的替换后的template_*.S**
   - 在通过 main.py 将 `resource/riscv/template.S` 转换成 `target/template_*.S` 时
   - **输出文件命名规则**：
     - 基于测试用例的 `arch.pretty-name` 和 `test-ins` 字段生成唯一文件名
     - 命名格式：`template_{pretty-name}_{changed-test-ins}.S`
     - 指令操作数中的逗号 (`,`)、空格等分隔符替换为下划线 (`_`)
     - 示例：
       - 输入：`pretty-name=riscv32d`, `test-ins=add x1,x1,x1`
       - 输出：`target/template_riscv32d_add_x1_x1_x1.S`

8. **Makefile构建脚本实现**
   - 实现 `Makefile`
   - 先通过 main.py 将 `resource/riscv/template.S` 转换成 `target/template_*.S`
   - 然后对每一个 `target/template_*.S` 编译，并生成可执行文件

#### 阶段 3：完善和集成（低优先级）

9. **错误处理**
   - 文件不存在错误
   - 格式验证错误
   - 友好的错误消息

10. **测试用例**
   - 单元测试
   - 集成测试


## 5. 使用示例

### 5.1 基本用法

```bash
# 使用显式模板路径
python3 main.py --template resource/riscv/template.S example.json --output_dir assembly_output

# 使用短选项
python3 main.py -t resource/riscv/template.S example.json -D assembly_output

# 使用默认模板路径（从 arch: riscv 推断）
python3 main.py example.json -D assembly_output
```

### 5.2 编译生成的汇编

```bash
# 生成并编译特定的测试用例
make compile-add

# 生成并编译所有测试用例
make run
```

---

## 6. 验收标准

### 6.1 功能验收

- [ ] 能够正确解析输入的 JSON 规范文件
- [ ] Value 类能正确解析二进制和十六进制位向量字面量
- [ ] 模板占位符能被正确替换为对应的值
- [ ] 缺失的 isa-state 值能正确默认为 0
- [ ] 生成的汇编文件能被 riscv-gcc 正确编译
- [ ] 支持命令行参数 `-t` 和 `-D`
- [ ] 支持从架构名称推断默认模板路径
- [ ] 在配置好Makefile后能make run一键运行

### 6.2 代码质量验收

- [ ] 代码符合 PEP 8 规范
- [ ] 关键类和方法有清晰的文档字符串
- [ ] 错误处理完善，错误消息友好
- [ ] 代码结构清晰，易于扩展其他架构

---

## 7. 相关文件

```
assembly-gen/
├── main.py              # 主入口点（待实现）
├── Makefile             # 构建和编译目标
├── README.md            # 使用文档
├── CLAUDE.md            # Claude Code 项目指导
├── draft.md             # 本草稿文档
└── resource/
    ├── example.json     # 示例输入规范
    └── riscv/
        └── template.S   # RISC-V 汇编模板（待创建）
```

---

## 8. 参考资料

- 父项目 `../isla/CLAUDE.md` - Isla 符号执行引擎文档
- `../rv32d.ir`, `../rv64d.ir` - Sail-RISC-V 生成的中间表示文件
- RISC-V 汇编参考手册
