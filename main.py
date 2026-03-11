#!/usr/bin/env python3
"""
Assembly-Gen: RISC-V 测试用例生成器

从 JSON 规范生成 RISC-V 汇编测试用例的框架。
使用模板驱动的文本替换系统，通过 JSON 规范中指定的 isa-state
替换模板文件中的预设占位符 ${xxx}，构建完整的 RISC-V 执行上下文。
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict


class Value:
    """
    表示位向量值，支持多种格式的输入和转换。

    支持的格式:
        - 二进制: "32'b0011_0101"、"8'b101"
        - 十六进制: "32'h80000000"、"8'hFF"
        - 带未知位: "32'b0011_00xx_0000_0101"

    属性:
        bits (int): 位宽
        value (int): 实际数值（无符号，未知位替换为 0）
        mask (int): 位掩码，1 表示有效位，0 表示未知位
        format (str): 'b' (二进制) 或 'h' (十六进制)

    示例:
        >>> Value("32'b0011_0101")
        >>> Value("32'h80000000")
        >>> Value("8'bxx01")  # 未知位
    """

    # 正则表达式匹配位向量格式：位宽'格式(值)
    # 格式: b(二进制) 或 h(十六进制)
    _PATTERN = re.compile(r"^(\d+)'([bh])([0-9a-fx_]+)$", re.IGNORECASE)

    def __init__(self, exp: str):
        """
        从字符串解析位向量。

        Args:
            exp: 位向量表达式，如 "32'b0011_0101" 或 "32'h80000000"

        Raises:
            ValueError: 如果表达式格式无效或数值超出位宽范围
        """
        if not isinstance(exp, str):
            raise ValueError(f"位向量表达式必须是字符串，收到: {type(exp)}")

        exp = exp.strip()
        match = self._PATTERN.match(exp)

        if not match:
            raise ValueError(
                f"无效的位向量格式: '{exp}'。"
                f"预期格式: <位宽>'<b|h><值>，如 32'b0011_0101 或 32'h80000000"
            )

        self.bits = int(match.group(1))
        self.format = match.group(2).lower()  # 'b' 或 'h'
        value_str = match.group(3).replace('_', '')  # 移除下划线

        # 验证位宽
        if self.bits <= 0:
            raise ValueError(f"位宽必须为正数，收到: {self.bits}")

        # 计算最大有效值（所有位都为 1 时的值）
        max_value = (1 << self.bits) - 1

        # 解析值并构建 mask
        try:
            if self.format == 'b':
                self.value, self.mask = self._parse_binary(value_str, max_value)
            else:  # 'h'
                self.value, self.mask = self._parse_hex(value_str, max_value)
        except ValueError as e:
            raise ValueError(f"无法解析位向量值 '{exp}': {e}")

        # 严格验证：数值必须落在位宽范围内
        if self.value > max_value:
            raise ValueError(
                f"位宽不匹配: 声明为 {self.bits} 位，"
                f"但值 0x{self.value:X} 超出范围（最大值: 0x{max_value:X}）"
            )

    def _parse_binary(self, value_str: str, max_value: int) -> tuple:
        """解析二进制格式，返回 (value, mask)。

        Mask 语义：1 表示该位已知，0 表示该位未知。
        零扩展的高位应标记为已知（值为 0）。
        """
        # 验证二进制字符串只包含 0、1 和 x
        if not all(c in '01x' for c in value_str):
            raise ValueError(
                f"二进制格式只能包含 0、1 和 x，收到: {value_str}"
            )

        # 验证位宽匹配（包括 x 位）
        if len(value_str) > self.bits:
            raise ValueError(
                f"位宽不匹配: 声明为 {self.bits} 位，"
                f"但提供了 {len(value_str)} 位二进制值"
            )

        # 构建 value 和 mask
        value = 0
        mask = (1 << self.bits) - 1  # 初始化：所有位都已知

        for i, c in enumerate(reversed(value_str)):
            bit_pos = i
            if c == '1':
                value |= (1 << bit_pos)
                # mask 位已置 1（已知）
            elif c == '0':
                # mask 位已置 1（已知）
                pass
            elif c == 'x':
                # x 位：标记为未知
                mask &= ~(1 << bit_pos)

        return value, mask

    def _parse_hex(self, value_str: str, max_value: int) -> tuple:
        """解析十六进制格式，返回 (value, mask)。

        Mask 语义：1 表示该位已知，0 表示该位未知。
        零扩展的高位应标记为已知（值为 0）。
        """
        # 验证十六进制字符串
        if not all(c in '0123456789abcdefABCDEFx' for c in value_str):
            raise ValueError(
                f"十六进制格式只能包含 0-9、a-f 和 x，收到: {value_str}"
            )

        # 验证位宽匹配（每个十六进制字符代表 4 位）
        max_hex_chars = (self.bits + 3) // 4
        if len(value_str) > max_hex_chars:
            raise ValueError(
                f"位宽不匹配: 声明为 {self.bits} 位，"
                f"但提供了 {len(value_str)} 个十六进制字符（最多 {max_hex_chars} 个）"
            )

        # 构建 value 和 mask
        value = 0
        mask = (1 << self.bits) - 1  # 初始化：所有位都已知

        for i, c in enumerate(reversed(value_str)):
            nibble_pos = i * 4
            if c == 'x':
                # x 位：标记这 4 位为未知
                mask &= ~(0xF << nibble_pos)
                continue
            # 解析十六进制字符
            nibble_value = int(c, 16)
            value |= (nibble_value << nibble_pos)
            # mask 位已置 1（已知）

        return value, mask

    def to_hex(self) -> str:
        """
        转换为十六进制字符串。

        Returns:
            十六进制字符串，如 "0x00000035" 或 "0x80000000"

        示例:
            >>> Value("32'b0011_0101").to_hex()
            '0x00000035'
            >>> Value("32'h80000000").to_hex()
            '0x80000000'
        """
        # 根据位宽计算需要的十六进制位数
        hex_digits = max(1, (self.bits + 3) // 4)

        # 应用位掩码
        masked_value = self.value & ((1 << self.bits) - 1)

        return f"0x{masked_value:0{hex_digits}X}"

    def to_bin(self) -> str:
        """
        转换为二进制字符串。

        Returns:
            二进制字符串，如 "0b00110101" 或 "0b1000000000000000"

        示例:
            >>> Value("8'b101").to_bin()
            '0b00000101'
        """
        binary_digits = max(1, self.bits)
        masked_value = self.value & ((1 << self.bits) - 1)
        return f"0b{masked_value:0{binary_digits}b}"

    def to_dec(self) -> str:
        """
        返回十进制整数字符串。

        Returns:
            十进制整数字符串

        示例:
            >>> Value("32'b0011_0101").to_dec()
            '53'
        """
        return str(self.value)

    def to_num(self) -> int:
        """
        返回整数值。

        Returns:
            整数值

        示例:
            >>> Value("32'b0011_0101").to_num()
            53
            >>> Value("32'h80000000").to_num()
            2147483648
        """
        return self.value

    def has_unknown_bits(self) -> bool:
        """
        检查是否有未知位（mask 不完整）。

        Returns:
            如果有未知位返回 True，否则返回 False
        """
        full_mask = (1 << self.bits) - 1
        return self.mask != full_mask

    def __repr__(self) -> str:
        return f"Value('{self.bits}\"{self.format}{self.value:X}')"


class GenericTarget:
    """
    架构目标基类，定义通用接口。

    属性:
        json_data: 原始 JSON 规范
        arch: 架构配置信息
        isa_state: ISA 状态
        test_ins: 测试指令
        template_path: 模板文件路径
    """

    def __init__(self, json_data: Dict[str, Any], template_path: str):
        """
        初始化架构目标。

        Args:
            json_data: 测试用例的 JSON 规范
            template_path: 模板文件路径
        """
        self.json_data = json_data
        self.arch = json_data.get("arch", {})
        self.isa_state = json_data.get("isa-state", {})
        self.test_ins = json_data.get("test-ins", "")
        self.template_path = template_path

    def get_arch(self) -> Dict[str, Any]:
        """返回架构信息。"""
        return self.arch

    def get_isa_state(self) -> Dict[str, Any]:
        """返回 ISA 状态。"""
        return self.isa_state

    def parse_template(self, template: str) -> str:
        """
        解析模板，替换占位符。

        Args:
            template: 模板内容

        Returns:
            替换后的模板内容

        Raises:
            NotImplementedError: 子类必须实现此方法
        """
        raise NotImplementedError("子类必须实现 parse_template 方法")

    def gen_assembly(self) -> str:
        """
        生成完整汇编代码。

        Returns:
            汇编代码字符串

        Raises:
            FileNotFoundError: 如果模板文件不存在
        """
        template_file = Path(self.template_path)
        if not template_file.exists():
            raise FileNotFoundError(f"模板文件不存在: {self.template_path}")

        with open(template_file, 'r', encoding='utf-8') as f:
            template_content = f.read()

        return self.parse_template(template_content)


class RISCV(GenericTarget):
    """
    RISC-V 架构实现。

    属性:
        xlen: 位宽 (32 或 64)
        ext: 扩展集 (如 "IMACFD")
        arch_name: 架构名称
    """

    # RISC-V CSR 寄存器列表
    CSR_REGISTERS = [
        "mstatus", "misa", "mie", "mtvec", "mepc", "mcause",
        "mtval", "mip", "mcycle", "minstret", "mcounteren",
        "mvendorid", "marchid", "mimpid", "mhartid",
        "status", "ie", "tvec", "epc", "cause", "tval", "ip",
        "satp", "scause", "stval", "sepc", "stvec",
        "fp", "fs", "xs", "sd"
    ]

    def __init__(self, json_data: Dict[str, Any], template_path: str):
        """
        初始化 RISC-V 架构目标。

        Args:
            json_data: 测试用例的 JSON 规范
            template_path: 模板文件路径

        Raises:
            ValueError: 如果架构名称不是 riscv 或 xlen 无效
        """
        super().__init__(json_data, template_path)

        self.arch_name = self.arch.get("name", "").lower()
        if self.arch_name != "riscv":
            raise ValueError(f"不支持的架构名称: {self.arch_name}，期望: riscv")

        # 解析 xlen
        xlen_str = self.arch.get("xlen", "32")
        try:
            self.xlen = int(xlen_str)
        except ValueError:
            raise ValueError(f"无效的 xlen 值: {xlen_str}，期望 32 或 64")

        if self.xlen not in (32, 64):
            raise ValueError(f"无效的 xlen 值: {self.xlen}，期望 32 或 64")

        self.ext = self.arch.get("ext", "")

        # 构建 ISA 状态表（GPR + CSR）
        self.gprs = [f"x{i}" for i in range(32)]

    def parse_template(self, template: str) -> str:
        """
        用 isa_state 中的值替换 ${register} 占位符。

        缺失的值默认为 0。

        Args:
            template: 模板内容

        Returns:
            替换后的模板内容

        Raises:
            ValueError: 如果占位符解析失败或替换后仍有残留占位符
        """
        result = template

        # 第一步：构建完整的占位符值映射（所有 GPR 和受支持 CSR）
        # 这样可以确保缺失值统一填 0，且所有 Value 解析错误都会立即报告
        placeholder_map = {}

        # 添加 GPR 值
        for reg in self.gprs:
            value_str = self.isa_state.get(reg, f"{self.xlen}'h0")
            placeholder_map[f"${{{reg}}}"] = Value(value_str).to_hex()

        # 添加 CSR 值（从 isa_state["csrs"] 或默认为 0）
        csr_values = self.isa_state.get("csrs", {})
        for csr_name in self.CSR_REGISTERS:
            if csr_name in csr_values:
                value_str = csr_values[csr_name]
            else:
                value_str = f"{self.xlen}'h0"
            placeholder_map[f"${{{csr_name}}}"] = Value(value_str).to_hex()

        # 第二步：执行所有占位符替换
        for placeholder, value in placeholder_map.items():
            result = result.replace(placeholder, value)

        # 第三步：替换测试指令和架构元数据占位符
        pretty_name = self.arch.get("pretty-name", f"rv{self.xlen}d")
        result = result.replace("${test_ins}", self.test_ins)
        result = result.replace("${pretty_name}", pretty_name)
        result = result.replace("${xlen}", str(self.xlen))

        # 构建用于元数据头部的扩展字符串
        # 模板使用 CSR 指令（csrw mstatus, csrw mepc），现代工具链需要 zicsr 扩展
        display_ext = self.ext
        if display_ext:
            # 检查是否已包含 zicsr（不区分大小写）
            ext_lower = display_ext.lower()
            if "zicsr" not in ext_lower:
                # 添加 zicsr 扩展（模板使用 CSR 指令）
                display_ext = display_ext + "zicsr"
        else:
            # 空扩展时，添加 zicsr
            display_ext = "zicsr"
        result = result.replace("${ext}", display_ext)

        # 第四步：检测残留的占位符或格式错误的占位符
        import re as re_module

        # 首先检查是否有格式错误的占位符（如 ${x 缺少闭合括号）
        # 查找所有 ${ 后面不跟 }...} 的模式
        malformed_pattern = re_module.compile(r'\$\{[^}]*$|\$\{[^}]*[^\s$}]')
        # 实际上更简单的方式：检查是否有 ${ 且后面没有对应的 }
        # 使用负向后查找来找到 ${ 后面没有 } 的情况
        open_brace_pattern = re_module.compile(r'\$\{[^}]*\}')

        # 检查未闭合的 ${ - 在字符串中间或末尾
        for match in re_module.finditer(r'\$\{', result):
            # 从 ${ 开始查找下一个 }
            start = match.start()
            rest_of_string = result[start:]
            # 检查是否在 rest_of_string 中有 }
            if '}' not in rest_of_string:
                # 没有 } ，格式错误
                raise ValueError(
                    f"模板中包含格式错误的占位符: {result[start:start+20]}...。"
                    f"占位符必须格式为 ${{name}}"
                )
            # 检查 } 之前是否有内容（${} 是无效的）
            after_brace = result[start+2:]
            if after_brace.startswith('}'):
                raise ValueError(
                    f"模板中包含空的占位符: ${{}}。"
                    f"占位符必须格式为 ${{name}}"
                )

        # 查找所有 ${...} 模式
        placeholder_pattern = re_module.compile(r'\$\{[^}]+\}')
        remaining_placeholders = placeholder_pattern.findall(result)

        if remaining_placeholders:
            # 有未替换的占位符
            unique_unmatched = set(remaining_placeholders)
            raise ValueError(
                f"模板中包含 {len(unique_unmatched)} 个未替换的占位符: "
                f"{', '.join(sorted(unique_unmatched))}。"
                f"请检查这些占位符是否受支持。"
            )

        return result


def sanitize_filename(name: str) -> str:
    """
    清理文件名，移除或替换不安全的字符。

    Args:
        name: 原始名称

    Returns:
        清理后的名称
    """
    # 替换文件系统不安全的字符
    unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    result = name
    for char in unsafe_chars:
        result = result.replace(char, '_')

    # 替换空格和逗号为下划线
    result = result.replace(' ', '_').replace(',', '_')

    return result


def generate_output_filename(pretty_name: str, test_ins: str) -> str:
    """
    生成输出文件名。

    命名格式: template_{pretty-name}_{sanitized-test-ins}.S

    Args:
        pretty_name: 架构的 pretty-name
        test_ins: 测试指令

    Returns:
        输出文件名

    示例:
        >>> generate_output_filename("rv32d", "add x1,x1,x1")
        'template_rv32d_add_x1_x1_x1.S'
    """
    sanitized_ins = sanitize_filename(test_ins)
    return f"template_{pretty_name}_{sanitized_ins}.S"


def validate_json_spec(json_data: Dict[str, Any]) -> None:
    """
    验证 JSON 规范的必需字段。

    Args:
        json_data: JSON 数据

    Raises:
        ValueError: 如果缺少必需字段或字段值无效
    """
    # 检查顶层 gen 字段
    if "gen" not in json_data:
        raise ValueError("JSON 规范缺少必需字段: 'gen'")

    gen = json_data["gen"]
    if not isinstance(gen, list):
        raise ValueError("'gen' 字段必须是数组")

    if len(gen) == 0:
        raise ValueError("'gen' 数组不能为空")

    # 验证每个测试用例
    for idx, test_case in enumerate(gen):
        prefix = f"测试用例 #{idx}"

        # 检查 arch 字段
        if "arch" not in test_case:
            raise ValueError(f"{prefix}: 缺少必需字段 'arch'")

        arch = test_case["arch"]
        if "name" not in arch:
            raise ValueError(f"{prefix}: arch 缺少必需字段 'name'")
        if "xlen" not in arch:
            raise ValueError(f"{prefix}: arch 缺少必需字段 'xlen'")

        # 检查 xlen 值
        xlen_str = arch["xlen"]

        # 首先检查是否为数字
        try:
            xlen = int(xlen_str)
        except ValueError:
            raise ValueError(f"{prefix}: arch.xlen 必须是数字，收到: {xlen_str}")

        # 然后检查是否为有效值
        if xlen not in (32, 64):
            raise ValueError(f"{prefix}: arch.xlen 必须是 32 或 64，收到: {xlen}")

        # 检查 test-ins 字段
        if "test-ins" not in test_case:
            raise ValueError(f"{prefix}: 缺少必需字段 'test-ins'")

        # 检查 isa-state 字段
        if "isa-state" not in test_case:
            raise ValueError(f"{prefix}: 缺少必需字段 'isa-state'")


def load_json_spec(json_path: str) -> Dict[str, Any]:
    """
    加载并解析 JSON 规范文件。

    Args:
        json_path: JSON 文件路径

    Returns:
        解析后的 JSON 数据

    Raises:
        FileNotFoundError: 如果文件不存在
        ValueError: 如果 JSON 格式无效或缺少必需字段
    """
    json_file = Path(json_path)
    if not json_file.exists():
        raise FileNotFoundError(f"JSON 文件不存在: {json_path}")

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 格式无效: {e}")

    # 验证 JSON 规范
    validate_json_spec(json_data)

    return json_data


def get_default_template_path(arch_name: str) -> str:
    """
    从架构名称推断默认模板路径。

    Args:
        arch_name: 架构名称

    Returns:
        默认模板路径
    """
    return f"resource/{arch_name}/template.S"


def process_test_cases(
    json_data: Dict[str, Any],
    template_path: str,
    output_dir: str,
    force_overwrite: bool = False
) -> list:
    """
    处理所有测试用例，生成汇编文件。

    Args:
        json_data: JSON 规范数据
        template_path: 模板文件路径
        output_dir: 输出目录
        force_overwrite: 是否强制覆盖已存在的文件

    Returns:
        生成的文件路径列表

    Raises:
        Exception: 如果生成失败
        ValueError: 如果输出文件冲突且内容不同
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    generated_files = []

    for test_case in json_data["gen"]:
        # 根据架构创建目标对象
        arch_name = test_case["arch"]["name"]

        if arch_name.lower() == "riscv":
            target = RISCV(test_case, template_path)
        else:
            raise ValueError(f"不支持的架构: {arch_name}")

        # 生成汇编代码
        assembly_code = target.gen_assembly()

        # 生成输出文件名
        pretty_name = test_case["arch"].get("pretty-name", f"rv{target.xlen}d")
        test_ins = test_case["test-ins"]
        filename = generate_output_filename(pretty_name, test_ins)
        output_file = output_path / filename

        # 检查文件是否已存在
        if output_file.exists():
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_content = f.read()

            if existing_content == assembly_code:
                # 内容相同，跳过写入
                print(f"跳过: {output_file} (内容相同)")
                generated_files.append(str(output_file))
                continue
            else:
                # 内容不同，需要处理冲突
                if force_overwrite:
                    print(f"覆盖: {output_file} (内容不同)")
                else:
                    raise ValueError(
                        f"输出文件冲突: {output_file} 已存在且内容不同。"
                        f"使用 --force-overwrite 或 -F 选项强制覆盖。"
                    )

        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(assembly_code)

        generated_files.append(str(output_file))
        print(f"生成: {output_file}")

    return generated_files


def main():
    """主入口点。"""
    parser = argparse.ArgumentParser(
        description="Assembly-Gen: RISC-V 测试用例生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s example.json -D assembly_output
  %(prog)s -t resource/riscv/template.S example.json -D assembly_output
        """
    )

    parser.add_argument(
        'json_file',
        help='JSON 规范文件路径'
    )

    parser.add_argument(
        '-t', '--template',
        dest='template',
        help='模板文件路径（默认: 从架构名称推断）'
    )

    parser.add_argument(
        '-D', '--output_dir',
        dest='output_dir',
        default='target',
        help='输出目录（默认: target）'
    )

    parser.add_argument(
        '-F', '--force-overwrite',
        dest='force_overwrite',
        action='store_true',
        help='强制覆盖已存在的输出文件'
    )

    args = parser.parse_args()

    try:
        # 加载 JSON 规范
        json_data = load_json_spec(args.json_file)

        # 确定模板路径
        if args.template:
            template_path = args.template
        else:
            # 从第一个测试用例的架构名称推断
            arch_name = json_data["gen"][0]["arch"]["name"]
            template_path = get_default_template_path(arch_name)

        # 处理测试用例
        generated_files = process_test_cases(
            json_data,
            template_path,
            args.output_dir,
            args.force_overwrite
        )

        print(f"\n成功生成 {len(generated_files)} 个汇编文件")

        return 0

    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期的错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
