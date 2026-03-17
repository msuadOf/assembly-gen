#!/usr/bin/env python3
"""
RISC-V 汇编模板生成工具

用于从手写模板 template_handwritten.S 生成标准模板文件。
支持 CSR/FPR/GPR 寄存器初始化代码的自动生成和开关控制。

默认启用所有寄存器类型的替换，可通过 --xxx=false 禁用特定类型。
"""

import argparse
from pathlib import Path


# 默认模板路径
DEFAULT_TEMPLATE = Path(__file__).parent / "template_handwritten.S"


def read_template(template_path: str) -> str:
    """读取模板文件内容"""
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def substitute(template: str, **kwargs) -> str:
    """
    执行字符串替换，自动处理缩进对齐

    Args:
        template: 模板内容
        **kwargs: 键值对，用于替换模板中的 ${key} 占位符

    Returns:
        替换后的内容
    """
    result = template
    # type: (str, Any)

    # ===== 遍历替换每个占位符 =====
    for key, value in kwargs.items():
        # ===== 构造占位符 =====
        placeholder = "${%s}" % key

        # ===== 检测占位符所在行的缩进（自适应 tab/空格）=====
        indent = ""
        for line in result.split("\n"):
            if placeholder in line:
                # 获取占位符前的所有空白字符作为缩进
                indent = line.split(placeholder)[0]
                break

        # ===== 处理替换值的缩进对齐 =====
        value_str = str(value)

        if "\n" in value_str:
            # 多行值：构建替换内容（第一行直接替换，后续行添加换行和缩进）
            lines = value_str.split("\n")
            # 第一行不额外加缩进（模板已有），后续行加 indent
            first_line = lines[0].lstrip()
            rest_lines = "\n".join(
                indent + line.lstrip() if line.strip() else ""
                for line in lines[1:]
            )
            value_str = first_line + "\n" + rest_lines
        else:
            # 单行值：去除原缩进（模板已有，不额外加）
            value_str = value_str.lstrip()

        # ===== 执行替换：把缩进+占位符一起替换，避免重复缩进 =====
        result = result.replace(indent + placeholder, indent + value_str)

    # ===== 返回结果 =====
    return result


def main():
    parser = argparse.ArgumentParser(
        description="RISC-V 汇编模板生成工具 - 从手写模板生成标准模板文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 默认生成所有寄存器初始化代码（CSR、FPR、GPR）
  python convert_handwritten.py

  # 禁用 CSR 替换（生成空内容）
  python convert_handwritten.py --csr=false

  # 禁用多个寄存器类型
  python convert_handwritten.py --csr=false --fpr=false

  # 使用自定义模板文件并输出到指定文件
  python convert_handwritten.py -t custom.S -o output.S

  # 仅启用 GPR 替换（禁用 CSR 和 FPR）
  python convert_handwritten.py --csr=false --fpr=false --gpr
        """
    )

    parser.add_argument(
        "--template", "-t",
        type=str,
        default=str(DEFAULT_TEMPLATE),
        help=f"模板文件路径 (默认: {DEFAULT_TEMPLATE})"
    )

    parser.add_argument(
        "--csr", "--csrs",
        nargs="?",
        const="true",
        default="true",
        help="CSR（控制状态寄存器）开关：默认启用，使用 --csr=false 禁用"
    )

    parser.add_argument(
        "--fpr", "--fprs",
        nargs="?",
        const="true",
        default="true",
        help="FPR（浮点寄存器）开关：默认启用，使用 --fpr=false 禁用"
    )

    parser.add_argument(
        "--gpr", "--gprs",
        nargs="?",
        const="true",
        default="true",
        help="GPR（通用寄存器）开关：默认启用，使用 --gpr=false 禁用"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径 (默认: 输出到 stdout)"
    )

    args = parser.parse_args()

    # 读取模板
    template = read_template(args.template)

    # 构造 CSR 设置代码
    csrs_list = ["mstatus", "mepc"]
    csr_codes = [
        "SET_CSR %s, t1, ${%s_VAL}" % (name, name.upper())
        for name in csrs_list
    ]
    csr_content = "\n".join(csr_codes)

    # 构造 GPR 设置代码
    gprs_list = [f"x{i}" for i in range(1, 32)]  # x1-x31
    gpr_codes = [
        "li %s, ${%s_VAL}" % (name, name.upper())
        for name in gprs_list
    ]
    gpr_content = "\n".join(gpr_codes)

    # 构造 FPR 设置代码
    fprs_list = [f"f{i}" for i in range(32)]  # f0-f31
    fpr_codes = [
        "flw %s, ${%s_VAL}(sp)" % (name, name.upper())
        for name in fprs_list
    ]
    fpr_content = "\n".join(fpr_codes)

    # 执行替换
    result = substitute(
        template,
        CSRs=csr_content if args.csr != "false" else "",
        FPRs=fpr_content if args.fpr != "false" else "",
        GPRs=gpr_content if args.gpr != "false" else "",
    )

    # 输出结果
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"结果已写入: {args.output}")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
