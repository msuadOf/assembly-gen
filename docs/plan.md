# Assembly-Gen RISC-V 测试用例生成器实现计划

## 目标描述

开发一个从 JSON 规范生成 RISC-V 汇编测试用例的框架。该框架使用模板驱动的文本替换系统，通过 JSON 规范中指定的 `isa-state` 替换模板文件中的预设占位符 `${xxx}`，快速构建完整的 RISC-V 执行上下文，为待测试指令提供指定的执行环境。

## 验收标准

遵循 TDD 理念，每个标准包含正向测试（预期通过）和负向测试（预期失败）。

### AC-1: JSON 规范解析

系统必须能够正确解析输入的 JSON 规范文件。

- 正向测试（预期通过）：
  - 解析包含完整 `gen` 数组的有效 JSON 文件
  - 解析包含 `arch`、`test-ins`、`isa-state` 字段的测试用例
  - 解析包含 `csrs` 嵌套对象的 `isa-state`
  - 解析多个测试用例（`gen` 数组包含多个元素）

- 负向测试（预期失败）：
  - 拒绝格式无效的 JSON 文件，并给出明确的错误信息
  - 拒绝缺少必需字段（`gen`、`arch.name`、`arch.xlen`、`test-ins`、`isa-state`）的 JSON
  - 拒绝 `arch.xlen` 不是 32 或 64 的值
  - 拒绝空文件或非 JSON 格式的输入

### AC-2: 位向量字面量解析

Value 类必须能够正确解析二进制和十六进制位向量字面量。

- 正向测试（预期通过）：
  - 解析二进制格式：`"32'b0011_0101"` → 位宽32，值0x35
  - 解析十六进制格式：`"32'h80000000"` → 位宽32，值0x80000000
  - 解析八位二进制：`"8'b101"` → 位宽8，值0x05
  - 解析八位十六进制：`"8'hFF"` → 位宽8，值0xFF
  - 解析带下划线的格式：`"32'b0011_0101"` 与 `"32'b00110101"` 等价
  - `to_hex()` 方法返回正确的十六进制字符串（如 `"0x35"` 或 `"0x80000000"`）
  - `to_num()` 方法返回正确的整数值

- 负向测试（预期失败）：
  - 拒绝无效的格式：`"32'b0012"`（二进制包含2）
  - 拒绝位宽不匹配：`"32'b0011_0101_1111"`（超过32位）
  - 拒绝缺少前缀的格式：`"00110101"`（缺少 `32'b` 或类似前缀）
  - 拒绝未知的格式标识符：`"32'o0011"`（`o` 不是有效标识符）

### AC-3: 模板占位符替换

系统必须能够正确将模板占位符替换为对应的值。

- 正向测试（预期通过）：
  - 替换通用寄存器占位符：`${x0}` 到 `${x31}`
  - 替换 CSR 寄存器占位符：`${mstatus}`、`${mepc}` 等
  - 替换测试指令占位符：`${test_ins}`
  - 缺失的寄存器值默认替换为 0
  - 使用 `isa-state` 中提供的值进行替换

- 负向测试（预期失败）：
  - 未替换的占位符（如果值确实缺失）应报告警告或使用默认值
  - 拒绝格式错误的占位符（如 `${x` 缺少闭合括号）

### AC-4: 输出文件命名

生成的输出文件必须按照指定的命名规则命名。

- 正向测试（预期通过）：
  - 根据 `arch.pretty-name` 和 `test-ins` 生成唯一文件名
  - 命名格式：`template_{pretty-name}_{sanitized-test-ins}.S`
  - 指令操作数中的逗号、空格等分隔符替换为下划线
  - 示例：`pretty-name=riscv32d`, `test-ins=add x1,x1,x1` → `template_riscv32d_add_x1_x1_x1.S`
  - 示例：`pretty-name=rv64d`, `test-ins=mul a0,t0,t1` → `template_rv64d_mul_a0_t0_t1.S`

- 负向测试（预期失败）：
  - 拒绝生成与现有文件重名但内容不同的输出文件（或提供覆盖选项）
  - 处理指令中包含的文件系统不安全字符（如 `/`、`\`、`:`）

### AC-5: 汇编代码生成

生成的汇编文件必须能够被 RISC-V 工具链正确编译。

- 正向测试（预期通过）：
  - 生成的汇编文件包含头部信息（架构、测试指令元数据）
  - 生成的汇编文件包含初始化代码（设置 GPR 和 CSR）
  - 生成的汇编文件包含测试指令
  - 生成的汇编文件包含结束标记
  - 使用 `riscv-gcc` 能够成功编译生成的 `.S` 文件
  - 使用 `riscv-objcopy` 和 `riscv-objdump` 能够处理生成的目标文件

- 负向测试（预期失败）：
  - 拒绝生成语法错误的汇编代码（如无效的指令格式）
  - 检测并报告汇编编译失败的情况

### AC-6: 命令行参数处理

系统必须支持指定的命令行参数。

- 正向测试（预期通过）：
  - 使用 `--template` 或 `-t` 指定模板路径
  - 使用 `--output_dir` 或 `-D` 指定输出目录
  - 使用位置参数指定 JSON 文件路径
  - 从架构名称（`arch.name` 为 `riscv`）推断默认模板路径 `resource/riscv/template.S`
  - 示例：`python3 main.py -t resource/riscv/template.S example.json -D assembly_output`
  - 示例：`python3 main.py example.json -D assembly_output`（使用默认模板）

- 负向测试（预期失败）：
  - 拒绝不存在的 JSON 文件路径
  - 拒绝不存在的模板文件路径
  - 拒绝无写入权限的输出目录
  - 拒绝无效的命令行参数

### AC-7: Makefile 集成

配置好 Makefile 后，必须能够一键运行生成和编译流程。

- 正向测试（预期通过）：
  - 执行 `make run` 生成所有汇编文件并编译
  - 执行 `make compile-add` 生成并编译特定测试用例
  - 执行 `make clean` 清理生成的文件

- 负向测试（预期失败）：
  - 处理编译失败并报告错误
  - 处理模板生成失败并报告错误

### AC-8: 代码质量

实现代码必须符合指定的质量标准。

- 正向测试（预期通过）：
  - 代码符合 PEP 8 规范
  - 关键类和方法有清晰的文档字符串
  - 错误处理完善，错误消息友好
  - 代码结构清晰，易于扩展其他架构

- 负向测试（预期失败）：
  - 代码不应包含未使用的导入或变量
  - 代码不应有明显的性能问题（如不必要的字符串复制）

## 路径边界

路径边界定义了实现质量的 acceptable 范围和选择。

### 上限（最大 acceptable 范围）

完整的实现包含以下功能：

1. **Value 类**：完整实现所有方法（`to_hex()`、`to_bin()`、`to_dec()`、`to_num()`），支持二进制、十六进制、带未知位的位向量解析
2. **JSON 解析**：完整解析输入文件，验证 JSON 格式，提取测试用例规范，处理多个测试用例
3. **CLI 参数处理**：支持 `--template`/`-t`、`--output_dir`/`-D` 参数，支持从架构名称推断默认模板路径
4. **GenericTarget 基类**：定义完整的通用接口，实现所有基础方法
5. **RISCV 类**：完整的 GPR 列表（x0-x31）、CSR 列表、占位符替换逻辑、模板加载逻辑
6. **模板系统**：创建完整的 `resource/riscv/template.S` 文件，定义所有占位符格式和替换规则
7. **输出文件命名**：按照 `template_{pretty-name}_{sanitized-test-ins}.S` 规则生成唯一文件名
8. **Makefile**：完整的构建脚本，支持 `make run`、`make clean`、`make compile-*` 目标
9. **错误处理**：完善的错误处理机制，友好的错误消息
10. **测试**：单元测试覆盖核心功能，集成测试验证端到端流程

### 下限（最小 acceptable 范围）

最小 viable 实现包含以下功能：

1. **Value 类**：实现核心方法（`to_hex()`、`to_num()`），支持二进制、十六进制基本格式解析
2. **JSON 解析**：读取输入文件，基本验证，提取单个测试用例规范
3. **CLI 参数处理**：基本的参数解析，支持指定 JSON 文件路径和输出目录
4. **RISCV 类**：基本的 GPR 列表，简单的占位符替换（使用 `str.replace()`）
5. **模板系统**：创建基本的 `resource/riscv/template.S` 文件，包含必要的占位符
6. **输出文件命名**：生成可识别的输出文件名（可以使用简化规则）
7. **Makefile**：基本的编译目标，能够编译生成的汇编文件
8. **错误处理**：基本的异常处理，提供可理解的错误信息

### 允许的选择

- **可以使用**：
  - 标准库：`argparse`、`json`、`pathlib`、`re`
  - 字符串替换方法：`str.replace()` 或正则表达式 `re.sub()`
  - 文件操作：`open()`、`Path.read_text()`、`Path.write_text()`
  - 测试框架：`unittest` 或 `pytest`

- **不能使用**：
  - 第三方依赖（除非必要且已获批准）
  - 复杂的模板引擎（如 Jinja2），应保持简单的文本替换

### 确定性设计说明

draft.md 指定了以下确定性设计选择：
- **输入格式**：必须使用 JSON 格式
- **架构支持**：当前版本仅支持 RISC-V 架构
- **占位符格式**：必须使用 `${xxx}` 格式
- **输出文件命名规则**：必须使用 `template_{pretty-name}_{sanitized-test-ins}.S` 格式

## 可行性提示和建议

> **注意**：本部分仅供参考和理解。这些是概念性建议，不是规范性要求。

### 概念性方法

以下是 Value 类位向量解析的伪代码：

```python
class Value:
    def __init__(self, exp: str):
        # 解析格式：32'b0011_0101 或 32'h80000000
        match = re.match(r"(\d+)'([bh])([0-9a-fx_]+)", exp.lower())
        if not match:
            raise ValueError(f"Invalid bit vector format: {exp}")

        self.bits = int(match.group(1))
        self.format = match.group(2)  # 'b' 或 'h'

        # 移除下划线和未知位
        value_str = match.group(3).replace('_', '')

        if self.format == 'b':
            # 二进制：将 'x' 替换为 '0' 进行解析
            clean_str = value_str.replace('x', '0')
            self.value = int(clean_str, 2)
        else:  # 'h'
            # 十六进制：将 'x' 替换为 '0' 进行解析
            clean_str = value_str.replace('x', '0')
            self.value = int(clean_str, 16)

    def to_hex(self) -> str:
        # 根据 xlen 格式化输出
        if self.bits <= 32:
            return f"0x{self.value & 0xFFFFFFFF:08X}"
        else:
            return f"0x{self.value & 0xFFFFFFFFFFFFFFFF:016X}"

    def to_num(self) -> int:
        return self.value
```

占位符替换的实现思路：

```python
def parse_template(self, template: str) -> str:
    result = template
    # 替换 GPR
    for i in range(32):
        placeholder = f"${{x{i}}}"
        value = self.isa_state.get(f"x{i}", "0")
        result = result.replace(placeholder, Value(value).to_hex())

    # 替换 CSR
    if "csrs" in self.isa_state:
        for csr_name, csr_value in self.isa_state["csrs"].items():
            placeholder = f"${{{csr_name}}}"
            result = result.replace(placeholder, Value(csr_value).to_hex())

    # 替换测试指令
    result = result.replace("${test_ins}", self.test_ins)

    return result
```

### 相关参考

- `main.py` - 当前的主入口点实现框架
- `resource/example.json` - JSON 输入格式示例
- `resource/riscv/template.S` - RISC-V 汇编模板文件
- `Makefile` - 构建脚本
- `../isla/CLAUDE.md` - Isla 符号执行引擎文档
- RISC-V 汇编参考手册

## 依赖关系和顺序

### 里程碑

#### 里程碑 1: 核心基础组件

- **阶段 A**：Value 类实现
  - 实现位向量字面量解析
  - 实现 `to_hex()` 和 `to_num()` 方法
  - 添加基本的输入验证

- **阶段 B**：JSON 解析
  - 读取和解析 JSON 文件
  - 验证必需字段
  - 提取测试用例规范

- **阶段 C**：CLI 参数处理
  - 实现 `argparse` 配置
  - 支持基本参数（JSON 路径、输出目录）
  - 支持可选模板路径参数

#### 里程碑 2: 模板系统

- **步骤 1**：GenericTarget 基类
  - 定义通用接口
  - 实现 `__init__`、`get_arch()`、`get_isa_state()` 方法

- **步骤 2**：RISCV 类实现
  - 添加 GPR 列表（x0-x31）
  - 添加 CSR 列表
  - 实现 `parse_template()` 占位符替换
  - 实现 `gen_assembly()` 模板加载

- **步骤 3**：模板文件创建
  - 创建 `resource/riscv/template.S`
  - 定义占位符格式
  - 添加必要的汇编结构

#### 里程碑 3: 集成和构建

- **步骤 1**：输出文件命名
  - 实现 `template_{pretty-name}_{sanitized-test-ins}.S` 命名规则
  - 处理特殊字符转义

- **步骤 2**：Makefile 集成
  - 实现生成目标
  - 实现编译目标
  - 实现清理目标

- **步骤 3**：错误处理和测试
  - 添加完善的错误处理
  - 编写单元测试
  - 编写集成测试

### 依赖关系说明

- **Value 类**必须在 **JSON 解析**之前完成，因为 JSON 解析需要使用 Value 类处理位向量值
- **JSON 解析**和 **CLI 参数处理**可以并行开发
- **GenericTarget 基类**必须在 **RISCV 类**之前完成
- **模板文件创建**和 **RISCV 类**可以并行开发，但需要在集成时协调
- **输出文件命名**依赖于 **RISCV 类**完成
- **Makefile 集成**必须在所有核心功能完成后进行
- **错误处理**应贯穿所有开发阶段
- **测试**应与每个里程碑同步进行

## 实现说明

### 代码风格要求

- 实现代码和注释**不得**包含计划特定术语，如 "AC-"、"Milestone"、"Step"、"Phase" 或类似的工作流标记
- 这些术语仅用于计划文档，不应出现在生成的代码库中
- 代码中使用描述性、领域适当的命名

### 用户澄清记录

在计划生成过程中，通过用户澄清确认了以下设计决策：

1. **Value 类 mask 属性**：延迟到后期作为未来增强功能实现
2. **输出文件命名规则**：使用 draft.md 中描述的 `template_{pretty-name}_{sanitized-test-ins}.S` 格式
3. **验收标准方式**：采用混合方式（部分自动测试，部分手动验证）

### 注意事项

1. **未知位处理**：当前版本中，未知位 (`x`) 应替换为 `0` 进行解析。完整的 mask 功能已延期。
2. **RISC-V 工具链**：用户需要自行安装 RISC-V 工具链（riscv-gcc、riscv-objcopy、riscv-objdump）
3. **输出目录**：程序应自动创建不存在的输出目录
4. **错误消息**：所有错误消息应友好且可操作，提供明确的解决建议

--- Original Design Draft Start ---

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

--- Original Design Draft End ---
