#! /bin/env python3
import argparse
import json
import os
import re
import sys
from src import RISCV, assemgen_core


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """清理文件名中的特殊字符

    1. 保留括号 ()
    2. 多个连续下划线合并成一个
    3. 过长的文件名进行截尾

    Args:
        name: 原始名称
        max_length: 最大长度（不含扩展名.S）

    Returns:
        清理后的文件名部分（不含扩展名）
    """
    # 保留括号，其他非字母数字字符替换为下划线
    sanitized = re.sub(r"[^a-zA-Z0-9()]", "_", name)

    # 多个连续下划线合并成一个
    sanitized = re.sub(r"_+", "_", sanitized)

    # 去除首尾下划线
    sanitized = sanitized.strip("_")

    # 截尾
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized


def generate_output_filename(pretty_name: str, test_ins: str, ret_val: str = "") -> str:
    """生成输出文件名：pretty-name_test-ins_ret-val

    整体文件名长度限制在 250 字符以内（包含 .S 扩展名）
    """
    # 为每个部分分配最大长度，确保整体不超过 250 字符
    # 格式: pretty_test_ret.S 或 pretty_test.S
    # 预留空间给下划线、扩展名: "_test.S" 约占 20 字符
    max_part_length = 200

    sanitized_pretty = sanitize_filename(pretty_name, max_part_length)
    sanitized_test = sanitize_filename(test_ins, max_part_length)

    if ret_val:
        sanitized_ret = sanitize_filename(ret_val, max_part_length)
        # 如果三部分组合后过长，按比例缩短每部分
        base = f"{sanitized_pretty}_{sanitized_test}_{sanitized_ret}"
        if len(base) > 245:  # 留5字符给 .S
            # 按比例分配空间
            total_len = len(sanitized_pretty) + len(sanitized_test) + len(sanitized_ret)
            pretty_len = int(245 * len(sanitized_pretty) / total_len)
            test_len = int(245 * len(sanitized_test) / total_len)
            ret_len = 245 - pretty_len - test_len - 2  # 减去两个下划线
            sanitized_pretty = sanitize_filename(pretty_name, pretty_len)
            sanitized_test = sanitize_filename(test_ins, test_len)
            sanitized_ret = sanitize_filename(ret_val, ret_len)
            base = f"{sanitized_pretty}_{sanitized_test}_{sanitized_ret}"
        return f"{base}.S"
    else:
        # 如果两部分组合后过长，按比例缩短
        base = f"{sanitized_pretty}_{sanitized_test}"
        if len(base) > 246:  # 留4字符给 .S
            total_len = len(sanitized_pretty) + len(sanitized_test)
            pretty_len = int(246 * len(sanitized_pretty) / total_len)
            test_len = 246 - pretty_len - 1  # 减去一个下划线
            sanitized_pretty = sanitize_filename(pretty_name, pretty_len)
            sanitized_test = sanitize_filename(test_ins, test_len)
            base = f"{sanitized_pretty}_{sanitized_test}"
        return f"{base}.S"


def main(args):
    """主函数：根据模板和JSON配置生成汇编文件

    Args:
        args: 命令行参数列表（如sys.argv[1:]）
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="汇编代码生成器")
    parser.add_argument("--template", "-t", required=True, help="模板文件路径")
    parser.add_argument("--json", "-j", action="append", help="JSON配置文件路径（可多次指定）")
    parser.add_argument("--json-dir", help="JSON配置文件目录（遍历目录下所有JSON）")
    parser.add_argument("--output-dir", "-o", default="assembly_output", help="输出目录路径")
    parser.add_argument("-f", "--force", action="store_true", help="强制覆盖已存在的输出文件")

    parsed_args = parser.parse_args(args)

    # 验证参数：必须指定 --json 或 --json-dir
    if not parsed_args.json and not parsed_args.json_dir:
        parser.error("必须指定 --json 或 --json-dir 参数")

    # 读取模板文件
    with open(parsed_args.template, "r") as f:
        template = f.read()

    # 收集需要处理的JSON文件
    json_files = []
    if parsed_args.json:
        json_files.extend(parsed_args.json)
    if parsed_args.json_dir:
        for filename in os.listdir(parsed_args.json_dir):
            if filename.endswith(".json"):
                json_files.append(os.path.join(parsed_args.json_dir, filename))

    # 确保输出目录存在
    os.makedirs(parsed_args.output_dir, exist_ok=True)

    # 收集所有待生成的输出文件信息，统一检测冲突
    # output_entries: [(output_path, json_path, item_index, item, original_filename)]
    output_entries = []
    # 跟踪每个JSON文件中每个基础文件名的出现次数: json_path -> base_filename -> count
    json_file_counter = {}
    # 跟跨文件的输出文件冲突: base_filename -> (json_path, item_index)
    cross_file_conflicts = {}

    for json_path in json_files:
        with open(json_path, "r") as f:
            data = json.load(f)

        if json_path not in json_file_counter:
            json_file_counter[json_path] = {}

        for idx, item in enumerate(data.get("gen", [])):
            arch = item.get("arch", {})
            pretty_name = arch.get("pretty-name", "unknown")
            test_ins = item.get("test-ins", "test")
            ret_val = item.get("ret_val", "")
            base_filename = generate_output_filename(pretty_name, test_ins, ret_val)

            # 检查是否与其他JSON文件冲突
            if base_filename in cross_file_conflicts and cross_file_conflicts[base_filename][0] != json_path:
                prev_json, prev_idx = cross_file_conflicts[base_filename]
                print(f"错误: 输出文件名冲突 '{base_filename}' 在不同JSON文件中", file=sys.stderr)
                print(f"  - {json_path} 第 {idx + 1} 项", file=sys.stderr)
                print(f"  - {prev_json} 第 {prev_idx + 1} 项", file=sys.stderr)
                print(f"提示: 请修改 'pretty-name'、'test-ins' 或 'ret_val' 使输出文件名唯一", file=sys.stderr)
                sys.exit(255)

            # 处理同一JSON文件内的冲突，添加数字后缀
            counter = json_file_counter[json_path]
            if base_filename not in counter:
                counter[base_filename] = 1
                final_filename = base_filename
            else:
                counter[base_filename] += 1
                # 在 .S 之前插入数字
                name_without_ext = base_filename[:-2]
                final_filename = f"{name_without_ext}_{counter[base_filename]}.S"
                print(f"警告: {json_path} 中检测到重复文件名 '{base_filename}'，使用 '{final_filename}'", file=sys.stderr)

            cross_file_conflicts[base_filename] = (json_path, idx)
            output_path = os.path.join(parsed_args.output_dir, final_filename)
            output_entries.append((output_path, json_path, idx, item))

    # 检测文件是否已存在
    for output_path, _, _, _ in output_entries:
        if os.path.exists(output_path) and not parsed_args.force:
            print(f"错误: 文件已存在 {output_path}，使用 -f 覆盖", file=sys.stderr)
            sys.exit(255)

    # 生成文件
    for output_path, json_path, idx, item in output_entries:
        arch = item.get("arch", {})
        arch_name = arch.get("name", "")

        if arch_name == "riscv":
            target = RISCV(item)
        else:
            # 通用目标
            from src.assemgen_core import GenericTarget
            target = GenericTarget(item)

        # 生成汇编代码
        result = assemgen_core(target, template)

        # 写入输出文件
        with open(output_path, "w") as f:
            f.write(result)

        # print(f"生成文件: {output_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
