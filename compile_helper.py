#!/usr/bin/env python3
"""
Assembly-Gen 编译验证 helper 模块

提供统一的编译验证功能，供 Python 集成测试和 Makefile 共用。
支持 RISC-V GNU 工具链和 LLVM/clang 工具链。
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, List, Tuple


class CompileResult:
    """编译结果。"""

    def __init__(self, success: bool, stdout: str, stderr: str, returncode: int):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode

    def __str__(self) -> str:
        if self.success:
            return "编译成功"
        else:
            return f"编译失败 (返回码: {self.returncode})\n{self.stderr}"


class CompilerConfig:
    """编译器配置。"""

    # RISC-V 扩展的标准顺序
    EXTENSION_ORDER = "imafdlutcvhbzgsxky"

    # 已知的多字母扩展列表（用于解析）
    KNOWN_MULTI_LETTER_EXTENSIONS = [
        "zicsr", "zifencei", "zba", "zbb", "zbc", "zbs",
        "zfh", "zfhmin", "zdinx", "zfinx", "zhinx",
        "zkn", "zks", "zkt", "zve32f", "zve64d",
        "zmmul", "zbpbo", "zca", "zcb", "zcd", "zcf",
        "zce", "zcmp", "zcmt"
    ]

    # G 扩展简写展开为实际扩展
    # G = IMAFD_Zicsr_Zifencei (标准通用扩展集)
    G_EXPANSION = "imafd_zicsr_zifencei"

    def __init__(self, xlen: int, extensions: str = ""):
        """
        初始化编译器配置。

        Args:
            xlen: 位宽 (32 或 64)
            extensions: 扩展集 (如 "IMACFD", "I_zicsr_zifencei", "GC")
        """
        self.xlen = xlen
        self.raw_extensions = extensions
        # 解析并缓存扩展列表
        self._single_exts, self._multi_exts = self._parse_extensions()

    def _parse_extensions(self) -> tuple:
        """解析扩展字符串，返回 (单字母扩展列表, 多字母扩展列表)。

        使用基于 token 的解析，确保多字母扩展被正确识别和保留。
        支持 G 扩展简写自动展开。
        """
        if not self.raw_extensions:
            return (['i', 'm', 'a', 'c'], [])  # 默认扩展

        # 转为小写
        exts = self.raw_extensions.lower()

        # 先按下划线分割
        tokens = exts.split('_')

        single_exts = []
        multi_exts = []

        for token in tokens:
            if not token:
                continue

            # 检查是否为已知的多字母扩展
            if token in self.KNOWN_MULTI_LETTER_EXTENSIONS:
                multi_exts.append(token)
                continue
            elif len(token) > 1 and token[0] == 'z':
                # z 开头的扩展，视为多字母扩展（即使不在已知列表中）
                multi_exts.append(token)
                continue

            # 处理单字母扩展或混合 token
            i = 0
            while i < len(token):
                # 检查是否为已知的多字母扩展（从当前位置开始）
                matched_multi = False
                for known in sorted(self.KNOWN_MULTI_LETTER_EXTENSIONS, key=len, reverse=True):
                    if token[i:].startswith(known):
                        multi_exts.append(known)
                        i += len(known)
                        matched_multi = True
                        break
                if matched_multi:
                    continue

                # 检查是否为未知的 z 开头扩展
                if token[i] == 'z' and i + 1 < len(token) and token[i+1].isalpha():
                    j = i + 1
                    while j < len(token) and token[j].isalpha():
                        j += 1
                    multi_exts.append(token[i:j])
                    i = j
                    continue

                # 处理 G 扩展简写：展开为单字母 + 多字母扩展
                if token[i] == 'g':
                    single_exts.extend(['i', 'm', 'a', 'f', 'd'])
                    multi_exts.extend(['zicsr', 'zifencei'])
                    i += 1
                    continue

                # 普通单字母扩展
                if token[i].isalpha():
                    single_exts.append(token[i])
                i += 1

        # 去重并保持顺序
        seen_single = set()
        unique_single = []
        for ext in single_exts:
            if ext not in seen_single:
                unique_single.append(ext)
                seen_single.add(ext)

        seen_multi = set()
        unique_multi = []
        for ext in multi_exts:
            if ext not in seen_multi:
                unique_multi.append(ext)
                seen_multi.add(ext)

        return (unique_single, unique_multi)

    @property
    def ordered_extensions(self) -> str:
        """返回按标准顺序排序的扩展字符串。

        注意：此属性返回扁平化的字符串，不适用于多个多字母扩展的格式化。
        请使用 march 属性获取正确的 -march 字符串。
        """
        # 按标准顺序排序单字母扩展
        ordered_single = []
        added = set()
        for e in self.EXTENSION_ORDER:
            if e in self._single_exts and e not in added:
                ordered_single.append(e)
                added.add(e)

        # 添加不在标准列表中的单字母扩展
        for e in self._single_exts:
            if e not in added:
                ordered_single.append(e)
                added.add(e)

        # 确保基本扩展存在
        if 'i' not in added and 'e' not in added:
            ordered_single.insert(0, 'i')

        # 合并单字母和多字母扩展
        return ''.join(ordered_single) + ''.join(self._multi_exts)

    @property
    def march(self) -> str:
        """生成 -march 参数。

        RISC-V ISA 规范：单字母扩展直接连接，多字母扩展用下划线分隔。
        例如: rv32imafdc, rv32i_zicsr, rv32imafdc_zicsr_zifencei
        """
        base = "rv32" if self.xlen == 32 else "rv64"

        # 按标准顺序排序单字母扩展
        ordered_single = []
        added = set()
        for e in self.EXTENSION_ORDER:
            if e in self._single_exts and e not in added:
                ordered_single.append(e)
                added.add(e)

        # 添加不在标准列表中的单字母扩展
        for e in self._single_exts:
            if e not in added:
                ordered_single.append(e)
                added.add(e)

        # 确保基本扩展存在
        if 'i' not in added and 'e' not in added:
            ordered_single.insert(0, 'i')

        # 构建扩展字符串
        single_str = ''.join(ordered_single)

        if single_str and self._multi_exts:
            # 两种都有：单字母在前，多字母用下划线连接
            return f"{base}{single_str}_{'_'.join(self._multi_exts)}"
        elif single_str:
            # 只有单字母扩展
            return f"{base}{single_str}"
        elif self._multi_exts:
            # 只有多字母扩展
            return f"{base}_{'_'.join(self._multi_exts)}"
        else:
            # 没有扩展
            return base

    @property
    def mabi(self) -> str:
        """生成 -mabi 参数。"""
        return "ilp32" if self.xlen == 32 else "lp64"


def find_toolchain() -> Dict[str, str]:
    """
    查找可用的工具链。

    优先级：
    1. 环境变量指定的工具（最高优先级）
    2. RISC-V GNU 工具链 (riscv-gcc)
    3. LLVM/clang 工具链 (clang --target=riscv{32,64})

    Returns:
        工具链命令字典，包含 'gcc', 'objcopy', 'objdump'
    """
    # 检查工具是否可用
    def check_tool(name: str) -> Optional[str]:
        """检查工具是否可用。"""
        try:
            result = subprocess.run(
                [name, "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return name
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    # 检查是否为 RISC-V gcc（排除原生 gcc）
    def check_riscv_gcc(name: str) -> Optional[str]:
        """检查是否为 RISC-V gcc，并测试其是否能处理 RISC-V 选项。"""
        try:
            # 首先检查是否为 gcc
            result = subprocess.run(
                [name, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return None

            # 检查是否包含 riscv 标识
            if "riscv" not in result.stdout.lower() and "riscv" not in result.stderr.lower():
                return None

            # 验证能处理 RISC-V 选项（尝试编译空程序）
            test_result = subprocess.run(
                [name, "-march=rv32i", "-c", "-x", "assembler", "-"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # 如果成功或只输出警告而非错误，则认为是有效的 RISC-V gcc
            if test_result.returncode == 0 or "warning:" in test_result.stderr.lower():
                return name
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    tools = {}
    has_env_override = False

    # 最高优先级：检查环境变量（独立覆盖）
    # 用户可以只设置部分环境变量，其他工具自动检测
    env_gcc = os.environ.get("ASSEMBLY_GEN_GCC")
    env_objcopy = os.environ.get("ASSEMBLY_GEN_OBJCOPY")
    env_objdump = os.environ.get("ASSEMBLY_GEN_OBJDUMP")

    # 如果设置了任何环境变量，标记为有覆盖
    if env_gcc or env_objcopy or env_objdump:
        has_env_override = True

        # 设置 GCC（使用环境变量或自动检测）
        if env_gcc:
            tools["gcc"] = env_gcc
        else:
            # 尝试自动检测 RISC-V gcc（避免原生 gcc）
            tools["gcc"] = check_riscv_gcc("riscv-gcc") or check_riscv_gcc("riscv32-unknown-elf-gcc") or check_riscv_gcc("riscv64-unknown-elf-gcc")

        # 设置 objcopy（使用环境变量或自动检测）
        if env_objcopy:
            tools["objcopy"] = env_objcopy
        else:
            tools["objcopy"] = check_tool("riscv-objcopy") or check_tool("riscv32-unknown-elf-objcopy") or check_tool("riscv64-unknown-elf-objcopy") or check_tool("llvm-objcopy") or check_tool("objcopy")

        # 设置 objdump（使用环境变量或自动检测）
        if env_objdump:
            tools["objdump"] = env_objdump
        else:
            tools["objdump"] = check_tool("riscv-objdump") or check_tool("riscv32-unknown-elf-objdump") or check_tool("riscv64-unknown-elf-objdump") or check_tool("llvm-objdump") or check_tool("objdump")

        # 检测是否为 LLVM 工具链
        gcc_basename = os.path.basename(tools.get("gcc", ""))
        if "clang" in gcc_basename or gcc_basename == "clang":
            tools["source"] = "llvm"
        else:
            tools["source"] = "gnu"

        # 验证所有必需工具都已找到
        if not all(tools.get(k) for k in ["gcc", "objcopy", "objdump"]):
            # 环境覆盖不完整，回退到自动检测
            has_env_override = False
            tools = {}

    if has_env_override:
        return tools

    # 自动检测工具链（无环境变量覆盖或覆盖不完整）
    # 优先检查多架构工具链
    riscv_gcc = check_tool("riscv-gcc")
    riscv_objcopy = check_tool("riscv-objcopy")
    riscv_objdump = check_tool("riscv-objdump")

    if riscv_gcc and riscv_objcopy and riscv_objdump:
        tools["gcc"] = riscv_gcc
        tools["objcopy"] = riscv_objcopy
        tools["objdump"] = riscv_objdump
        tools["source"] = "gnu"
        return tools

    # 检查 32 位工具链
    riscv32_gcc = check_tool("riscv32-unknown-elf-gcc") or check_tool("riscv32-unknown-linux-gnu-gcc")
    riscv32_objcopy = check_tool("riscv32-unknown-elf-objcopy") or check_tool("riscv32-unknown-linux-gnu-objcopy")
    riscv32_objdump = check_tool("riscv32-unknown-elf-objdump") or check_tool("riscv32-unknown-linux-gnu-objdump")

    if riscv32_gcc and riscv32_objcopy and riscv32_objdump:
        tools["gcc"] = riscv32_gcc
        tools["objcopy"] = riscv32_objcopy
        tools["objdump"] = riscv32_objdump
        tools["source"] = "gnu"
        return tools

    # 检查 64 位工具链（仅作为备选）
    riscv64_gcc = check_tool("riscv64-unknown-elf-gcc") or check_tool("riscv64-unknown-linux-gnu-gcc")
    riscv64_objcopy = check_tool("riscv64-unknown-elf-objcopy") or check_tool("riscv64-unknown-linux-gnu-objcopy")
    riscv64_objdump = check_tool("riscv64-unknown-elf-objdump") or check_tool("riscv64-unknown-linux-gnu-objdump")

    if riscv64_gcc and riscv64_objcopy and riscv64_objdump:
        tools["gcc"] = riscv64_gcc
        tools["objcopy"] = riscv64_objcopy
        tools["objdump"] = riscv64_objdump
        tools["source"] = "gnu64"  # 标记为 64 位工具链
        return tools

    # 检查 LLVM/clang 工具链
    clang = check_tool("clang")
    llvm_objcopy = check_tool("llvm-objcopy")
    llvm_objdump = check_tool("llvm-objdump")

    if clang and llvm_objcopy and llvm_objdump:
        tools["gcc"] = clang  # 使用 clang 作为 gcc 替代
        tools["objcopy"] = llvm_objcopy
        tools["objdump"] = llvm_objdump
        tools["source"] = "llvm"
        return tools

    # 没有找到完整的工具链
    return {"source": "none"}


def compile_assembly(
    assembly_file: str,
    output_elf: str,
    config: CompilerConfig,
    linker_script: Optional[str] = None,
    tools: Optional[Dict[str, str]] = None
) -> CompileResult:
    """
    编译汇编文件为 ELF 格式。

    Args:
        assembly_file: 汇编文件路径
        output_elf: 输出 ELF 文件路径
        config: 编译器配置
        linker_script: 链接器脚本路径 (可选)
        tools: 工具链命令字典 (可选，自动检测)

    Returns:
        编译结果
    """
    if tools is None:
        tools = find_toolchain()

    if tools.get("source") == "none":
        return CompileResult(
            False, "", "错误: 未找到可用的 RISC-V 工具链", 1
        )

    # 构建编译命令
    cmd = [tools["gcc"]]

    # 添加架构参数
    if tools["source"] == "llvm":
        # LLVM/clang 使用 -target (不是 --target)
        # 目标三元组基于 xlen，扩展集通过 -march 传递
        target_triple = "riscv32" if config.xlen == 32 else "riscv64"
        cmd.extend(["-target", target_triple])
        # clang 也需要 -march 和 -mabi
        cmd.extend([f"-march={config.march}", f"-mabi={config.mabi}"])
    else:
        # GNU gcc 使用 -march 和 -mabi
        # 注意：某些 riscv-gnu-toolchain 版本使用等号格式
        cmd.extend([f"-march={config.march}", f"-mabi={config.mabi}"])

    # 添加其他选项
    cmd.extend(["-nostdlib", "-nostartfiles", "-ffreestanding"])

    # 添加链接器脚本
    if linker_script:
        cmd.extend(["-T", linker_script])

    # 添加输入输出文件
    cmd.extend([assembly_file, "-o", output_elf])

    # 执行编译
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        success = result.returncode == 0
        return CompileResult(
            success,
            result.stdout,
            result.stderr,
            result.returncode
        )
    except subprocess.TimeoutExpired:
        return CompileResult(
            False, "", "错误: 编译超时", 1
        )
    except Exception as e:
        return CompileResult(
            False, "", f"错误: {e}", 1
        )


def convert_elf(
    elf_file: str,
    output_hex: Optional[str] = None,
    output_bin: Optional[str] = None,
    output_dump: Optional[str] = None,
    tools: Optional[Dict[str, str]] = None
) -> Tuple[CompileResult, CompileResult, CompileResult]:
    """
    转换 ELF 文件为其他格式。

    Args:
        elf_file: ELF 文件路径
        output_hex: 输出 HEX 文件路径 (可选)
        output_bin: 输出 BIN 文件路径 (可选)
        output_dump: 输出 dump 文件路径 (可选)
        tools: 工具链命令字典 (可选，自动检测)

    Returns:
        (hex_result, bin_result, dump_result) 元组
    """
    if tools is None:
        tools = find_toolchain()

    hex_result = CompileResult(True, "", "", 0)
    bin_result = CompileResult(True, "", "", 0)
    dump_result = CompileResult(True, "", "", 0)

    if tools.get("source") == "none":
        error = "错误: 未找到可用的工具链"
        hex_result = CompileResult(False, "", error, 1)
        bin_result = CompileResult(False, "", error, 1)
        dump_result = CompileResult(False, "", error, 1)
        return hex_result, bin_result, dump_result

    # 转换为 HEX 格式
    if output_hex:
        try:
            result = subprocess.run(
                [tools["objcopy"], "-O", "ihex", elf_file, output_hex],
                capture_output=True,
                text=True,
                timeout=10
            )
            hex_result = CompileResult(
                result.returncode == 0,
                result.stdout,
                result.stderr,
                result.returncode
            )
        except Exception as e:
            hex_result = CompileResult(False, "", f"错误: {e}", 1)

    # 转换为 BIN 格式
    if output_bin:
        try:
            result = subprocess.run(
                [tools["objcopy"], "-O", "binary", elf_file, output_bin],
                capture_output=True,
                text=True,
                timeout=10
            )
            bin_result = CompileResult(
                result.returncode == 0,
                result.stdout,
                result.stderr,
                result.returncode
            )
        except Exception as e:
            bin_result = CompileResult(False, "", f"错误: {e}", 1)

    # 生成 dump 文件
    if output_dump:
        try:
            result = subprocess.run(
                [tools["objdump"], "-d", elf_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                with open(output_dump, 'w') as f:
                    f.write(result.stdout)
            dump_result = CompileResult(
                result.returncode == 0,
                result.stdout,
                result.stderr,
                result.returncode
            )
        except Exception as e:
            dump_result = CompileResult(False, "", f"错误: {e}", 1)

    return hex_result, bin_result, dump_result


def parse_assembly_metadata(assembly_file: str, strict: bool = False) -> CompilerConfig:
    """
    从生成的汇编文件头部解析架构元数据。

    汇编文件头部应包含如下格式的注释：
    # 架构: RISC-V (xlen=32, ext=IMACFD)

    Args:
        assembly_file: 汇编文件路径
        strict: 如果为 True，元数据缺失时抛出异常而不是回退到文件名猜测

    Returns:
        CompilerConfig 对象

    Raises:
        ValueError: 如果无法解析元数据（或在 strict 模式下元数据缺失）
        FileNotFoundError: 如果文件不存在
    """
    import re
    import os

    try:
        with open(assembly_file, 'r', encoding='utf-8') as f:
            # 只读取前 20 行，寻找元数据
            for i, line in enumerate(f):
                if i >= 20:
                    break

                # 查找 "架构: RISC-V (xlen=..., ext=...)" 模式
                # ext 可以为空，允许 ext= 格式
                match = re.search(r'架构:\s*RISC-V\s*\(\s*xlen=(\d+)\s*,\s*ext=([^\)]*)\s*\)', line)
                if match:
                    xlen = int(match.group(1))
                    ext = match.group(2).strip()  # strip 处理空格
                    return CompilerConfig(xlen, ext)
    except FileNotFoundError:
        raise
    except Exception as e:
        raise ValueError(f"无法从 {assembly_file} 解析架构元数据: {e}")

    # strict 模式下，元数据缺失时抛出异常
    if strict:
        raise ValueError(
            f"错误: 汇编文件 {assembly_file} 头部缺少必需的架构元数据注释。"
            f"请确保文件前 20 行包含如下格式的注释："
            f"# 架构: RISC-V (xlen=32, ext=IMACFD)"
        )

    # 非严格模式：如果未找到元数据，尝试从文件名推断（向后兼容）
    basename = os.path.basename(assembly_file)

    # 从文件名推断 xlen
    if 'rv64' in basename or '64d' in basename:
        xlen = 64
    else:
        xlen = 32

    # 使用默认扩展集
    ext = "IMACFD"

    return CompilerConfig(xlen, ext)


def compile_assembly_from_metadata(
    assembly_file: str,
    output_prefix: str,
    linker_script: Optional[str] = None,
    tools: Optional[Dict[str, str]] = None
) -> CompileResult:
    """
    从汇编文件读取元数据并编译。

    Args:
        assembly_file: 汇编文件路径
        output_prefix: 输出文件前缀（不含扩展名）
        linker_script: 链接器脚本路径 (可选)
        tools: 工具链命令字典 (可选，自动检测)

    Returns:
        编译结果
    """
    # 从汇编文件解析元数据（严格模式）
    config = parse_assembly_metadata(assembly_file, strict=True)

    # 编译为 ELF
    elf_file = f"{output_prefix}.elf"
    return compile_assembly(
        assembly_file,
        elf_file,
        config,
        linker_script,
        tools
    )


def compile_full_pipeline(
    assembly_file: str,
    output_prefix: str,
    config: CompilerConfig,
    linker_script: Optional[str] = None,
    tools: Optional[Dict[str, str]] = None
) -> Dict[str, CompileResult]:
    """
    执行完整的编译流程：汇编 -> ELF -> HEX/BIN/DUMP。

    Args:
        assembly_file: 汇编文件路径
        output_prefix: 输出文件前缀（不含扩展名）
        config: 编译器配置
        linker_script: 链接器脚本路径 (可选)
        tools: 工具链命令字典 (可选，自动检测)

    Returns:
        包含各阶段结果的字典
    """
    results = {}

    # 编译为 ELF
    elf_file = f"{output_prefix}.elf"
    results["elf"] = compile_assembly(
        assembly_file, elf_file, config, linker_script, tools
    )

    if not results["elf"].success:
        return results

    # 转换为其他格式
    hex_result, bin_result, dump_result = convert_elf(
        elf_file,
        f"{output_prefix}.hex" if results["elf"].success else None,
        f"{output_prefix}.bin" if results["elf"].success else None,
        f"{output_prefix}.dump" if results["elf"].success else None,
        tools
    )

    results["hex"] = hex_result
    results["bin"] = bin_result
    results["dump"] = dump_result

    return results


if __name__ == "__main__":
    # 命令行测试
    import argparse

    parser = argparse.ArgumentParser(description="测试编译工具链")
    parser.add_argument("assembly", nargs="?", help="汇编文件路径")
    parser.add_argument("-o", "--output", default="output", help="输出前缀")
    parser.add_argument("-x", "--xlen", type=int, default=32, choices=[32, 64], help="位宽")
    parser.add_argument("-e", "--extensions", default="", help="扩展集")
    parser.add_argument("-T", "--linker", help="链接器脚本")
    parser.add_argument("--from-metadata", action="store_true", help="从汇编文件头部解析 xlen 和扩展集")
    parser.add_argument("--version", action="store_true", help="显示版本信息并退出")

    args = parser.parse_args()

    # 处理 --version 标志
    if args.version:
        tools = find_toolchain()
        source = tools.get("source", "none")
        if source != "none":
            print(f"工具链来源: {source}")
            sys.exit(0)
        else:
            print("未找到可用的工具链")
            sys.exit(1)

    # 如果没有提供汇编文件，显示帮助信息
    if not args.assembly:
        parser.print_help()
        sys.exit(1)

    # 检测工具链
    tools = find_toolchain()
    print(f"工具链来源: {tools.get('source', 'none')}")
    if tools.get("source") == "none":
        print("错误: 未找到可用的工具链")
        sys.exit(1)

    # 编译
    if args.from_metadata:
        # 从汇编文件解析元数据并编译为 ELF
        print("从汇编文件解析元数据...")
        elf_result = compile_assembly_from_metadata(
            args.assembly,
            args.output,
            args.linker,
            tools
        )

        if not elf_result.success:
            print(f"编译失败: {elf_result.stderr}")
            sys.exit(1)

        # 转换为 HEX/BIN/DUMP 格式（保留与完整流程相同的输出）
        elf_file = f"{args.output}.elf"
        hex_result, bin_result, dump_result = convert_elf(
            elf_file,
            f"{args.output}.hex",
            f"{args.output}.bin",
            f"{args.output}.dump",
            tools
        )

        # 打印结果
        print(f"ELF: {elf_result}")
        print(f"HEX: {hex_result}")
        print(f"BIN: {bin_result}")
        print(f"DUMP: {dump_result}")

        # 如果任何格式转换失败，返回错误
        if not hex_result.success or not bin_result.success or not dump_result.success:
            if not hex_result.success:
                print(f"错误: HEX 转换失败: {hex_result.stderr}")
            if not bin_result.success:
                print(f"错误: BIN 转换失败: {bin_result.stderr}")
            if not dump_result.success:
                print(f"错误: DUMP 生成失败: {dump_result.stderr}")
            sys.exit(1)

        # 返回码基于 ELF 编译结果
        sys.exit(0)
    else:
        # 使用手动指定的参数
        config = CompilerConfig(args.xlen, args.extensions)
        print(f"编译配置: -march={config.march} -mabi={config.mabi}")

        results = compile_full_pipeline(
            args.assembly,
            args.output,
            config,
            args.linker,
            tools
        )

        # 打印结果
        for stage, result in results.items():
            print(f"{stage.upper()}: {result}")

        # 返回码
        sys.exit(0 if results["elf"].success else 1)
