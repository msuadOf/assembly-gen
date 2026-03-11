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

    示例:
        >>> Value("32'b0011_0101")
        >>> Value("32'h80000000")
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
            ValueError: 如果表达式格式无效
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

        # 解析值
        try:
            if self.format == 'b':
                # 二进制：将 'x' 替换为 '0' 进行解析
                clean_str = value_str.replace('x', '0')
                # 验证二进制字符串只包含 0 和 1（在替换 x 之后）
                if not all(c in '01' for c in clean_str):
                    raise ValueError(f"二进制格式只能包含 0、1 和 x，收到: {value_str}")
                # 验证位宽匹配
                if len(clean_str) > self.bits:
                    raise ValueError(
                        f"位宽不匹配: 声明为 {self.bits} 位，"
                        f"但提供了 {len(clean_str)} 位二进制值"
                    )
                self.value = int(clean_str, 2) if clean_str else 0
            else:  # 'h'
                # 十六进制：将 'x' 替换为 '0' 进行解析
                clean_str = value_str.replace('x', '0')
                # 验证十六进制字符串
                if not all(c in '0123456789abcdefABCDEF' for c in clean_str):
                    raise ValueError(f"十六进制格式只能包含 0-9、a-f 和 x，收到: {value_str}")
                # 验证位宽匹配（每个十六进制字符代表 4 位）
                max_hex_chars = (self.bits + 3) // 4
                if len(clean_str) > max_hex_chars:
                    raise ValueError(
                        f"位宽不匹配: 声明为 {self.bits} 位，"
                        f"但提供了 {len(clean_str)} 个十六进制字符（最多 {max_hex_chars} 个）"
                    )
                self.value = int(clean_str, 16) if clean_str else 0
        except ValueError as e:
            raise ValueError(f"无法解析位向量值 '{exp}': {e}")

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
        if self.bits <= 32:
            masked_value = self.value & 0xFFFFFFFF
        elif self.bits <= 64:
            masked_value = self.value & 0xFFFFFFFFFFFFFFFF
        else:
            masked_value = self.value & ((1 << self.bits) - 1)

        return f"0x{masked_value:0{hex_digits}X}"

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
        """
        result = template

        # 替换 GPR 占位符
        for reg in self.gprs:
            placeholder = f"${{{reg}}}"
            value_str = self.isa_state.get(reg, "0")
            try:
                value = Value(value_str).to_hex()
            except ValueError:
                # 如果解析失败，使用原始字符串或默认值
                value = value_str if value_str != "0" else "0x00000000"
            result = result.replace(placeholder, value)

        # 替换 CSR 占位符
        if "csrs" in self.isa_state:
            for csr_name, csr_value in self.isa_state["csrs"].items():
                placeholder = f"${{{csr_name}}}"
                try:
                    value = Value(csr_value).to_hex()
                except ValueError:
                    value = csr_value
                result = result.replace(placeholder, value)

        # 替换测试指令占位符
        result = result.replace("${test_ins}", self.test_ins)

        # 替换架构元数据占位符
        pretty_name = self.arch.get("pretty-name", f"rv{self.xlen}d")
        result = result.replace("${pretty_name}", pretty_name)
        result = result.replace("${xlen}", str(self.xlen))
        result = result.replace("${ext}", self.ext)

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
        try:
            xlen = int(arch["xlen"])
            if xlen not in (32, 64):
                raise ValueError(f"{prefix}: arch.xlen 必须是 32 或 64，收到: {xlen}")
        except ValueError:
            raise ValueError(f"{prefix}: arch.xlen 必须是数字，收到: {arch['xlen']}")

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
    output_dir: str
) -> list:
    """
    处理所有测试用例，生成汇编文件。

    Args:
        json_data: JSON 规范数据
        template_path: 模板文件路径
        output_dir: 输出目录

    Returns:
        生成的文件路径列表

    Raises:
        Exception: 如果生成失败
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
            args.output_dir
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
