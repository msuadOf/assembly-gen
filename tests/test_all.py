#!/usr/bin/env python3
"""
Assembly-Gen 单元测试和集成测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from pathlib import Path
from main import (
    Value,
    GenericTarget,
    RISCV,
    generate_output_filename,
    sanitize_filename,
    load_json_spec,
    validate_json_spec
)


class TestValue(unittest.TestCase):
    """测试 Value 类的位向量解析功能。"""

    def test_binary_parsing(self):
        """测试二进制格式解析。"""
        test_cases = [
            ("32'b0011_0101", "0x00000035", 53),
            ("32'b10101010", "0x000000AA", 170),
            ("8'b101", "0x05", 5),
            ("16'b1111000011110000", "0xF0F0", 61680),
        ]
        for exp, expected_hex, expected_num in test_cases:
            with self.subTest(exp=exp):
                v = Value(exp)
                self.assertEqual(v.to_hex(), expected_hex)
                self.assertEqual(v.to_num(), expected_num)

    def test_hex_parsing(self):
        """测试十六进制格式解析。"""
        test_cases = [
            ("32'h80000000", 0x80000000, 2147483648),
            ("8'hFF", 0xFF, 255),
            ("16'hDEAD", 0xDEAD, 57005),
            ("64'hFFFFFFFFFFFFFFFF", 0xFFFFFFFFFFFFFFFF, 2**64 - 1),
        ]
        for exp, expected_hex, expected_num in test_cases:
            with self.subTest(exp=exp):
                v = Value(exp)
                self.assertEqual(v.to_hex(), f"0x{expected_hex:0{max(2, (len(bin(expected_hex)) - 2) // 4)}X}")
                self.assertEqual(v.to_num(), expected_num)

    def test_underscore_handling(self):
        """测试下划线处理。"""
        v1 = Value("32'b0011_0101")
        v2 = Value("32'b00110101")
        self.assertEqual(v1.to_hex(), v2.to_hex())
        self.assertEqual(v1.to_num(), v2.to_num())

    def test_invalid_formats(self):
        """测试无效格式抛出异常。"""
        invalid_cases = [
            "32'b0012",      # 二进制包含 2
            "invalid",       # 完全无效
            "32'o0011",      # 未知格式标识符
            "0'b0011",       # 位宽为 0
        ]
        for case in invalid_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    Value(case)

    def test_small_bit_widths(self):
        """测试小位宽值。"""
        v = Value("8'hFF")
        self.assertEqual(v.to_hex(), "0xFF")
        self.assertEqual(v.to_num(), 255)


class TestFilenameGeneration(unittest.TestCase):
    """测试文件名生成功能。"""

    def test_generate_output_filename(self):
        """测试输出文件名生成。"""
        test_cases = [
            ("rv32d", "add x1,x1,x1", "template_rv32d_add_x1_x1_x1.S"),
            ("rv64d", "mul a0,t0,t1", "template_rv64d_mul_a0_t0_t1.S"),
            ("riscv32", "sub x10,x11,x12", "template_riscv32_sub_x10_x11_x12.S"),
        ]
        for pretty_name, test_ins, expected in test_cases:
            with self.subTest(pretty_name=pretty_name, test_ins=test_ins):
                result = generate_output_filename(pretty_name, test_ins)
                self.assertEqual(result, expected)

    def test_sanitize_filename(self):
        """测试文件名清理。"""
        test_cases = [
            ("add x1,x1,x1", "add_x1_x1_x1"),
            ("mul a0,t0,t1", "mul_a0_t0_t1"),
            ("test/file:name", "test_file_name"),
        ]
        for input_name, expected in test_cases:
            with self.subTest(input=input_name):
                result = sanitize_filename(input_name)
                self.assertEqual(result, expected)


class TestJSONParsing(unittest.TestCase):
    """测试 JSON 解析功能。"""

    def test_load_valid_json(self):
        """测试加载有效的 JSON 文件。"""
        json_path = "resource/example.json"
        data = load_json_spec(json_path)
        self.assertIn("gen", data)
        self.assertIsInstance(data["gen"], list)
        self.assertGreater(len(data["gen"]), 0)

    def test_validate_missing_gen_field(self):
        """测试缺少 gen 字段的验证。"""
        json_data = {}
        with self.assertRaises(ValueError) as context:
            validate_json_spec(json_data)
        self.assertIn("gen", str(context.exception))

    def test_validate_missing_arch_field(self):
        """测试缺少 arch 字段的验证。"""
        json_data = {"gen": [{"test-ins": "add x1,x1,x1"}]}
        with self.assertRaises(ValueError) as context:
            validate_json_spec(json_data)
        self.assertIn("arch", str(context.exception))

    def test_validate_invalid_xlen(self):
        """测试无效的 xlen 值。"""
        json_data = {
            "gen": [{
                "arch": {"name": "riscv", "xlen": "16"},
                "test-ins": "add x1,x1,x1",
                "isa-state": {}
            }]
        }
        with self.assertRaises(ValueError) as context:
            validate_json_spec(json_data)
        self.assertIn("xlen", str(context.exception))

    def test_nonexistent_file(self):
        """测试加载不存在的文件。"""
        with self.assertRaises(FileNotFoundError):
            load_json_spec("nonexistent.json")


class TestRISCVClass(unittest.TestCase):
    """测试 RISCV 类功能。"""

    def test_parse_template_gpr_replacement(self):
        """测试 GPR 占位符替换。"""
        json_data = {
            "arch": {"name": "riscv", "xlen": "32", "pretty-name": "rv32d"},
            "test-ins": "add x1,x1,x1",
            "isa-state": {"x1": "32'h00000001", "x2": "8'hFF"}
        }
        target = RISCV(json_data, "resource/riscv/template.S")
        template = "li x1, ${x1}\nli x2, ${x2}\nli x3, ${x3}"
        result = target.parse_template(template)
        self.assertIn("0x00000001", result)
        self.assertIn("0xFF", result)
        self.assertIn("0x00000000", result)  # x3 应该使用默认值 0

    def test_parse_template_csr_replacement(self):
        """测试 CSR 占位符替换。"""
        json_data = {
            "arch": {"name": "riscv", "xlen": "32", "pretty-name": "rv32d"},
            "test-ins": "add x1,x1,x1",
            "isa-state": {
                "csrs": {
                    "mstatus": "32'h00003000",
                    "mepc": "32'h80000000"
                }
            }
        }
        target = RISCV(json_data, "resource/riscv/template.S")
        template = "li t0, ${mstatus}\ncsrw mstatus, t0\nli t0, ${mepc}\ncsrw mepc, t0"
        result = target.parse_template(template)
        self.assertIn("0x00003000", result)
        self.assertIn("0x80000000", result)

    def test_invalid_architecture(self):
        """测试无效的架构名称。"""
        json_data = {
            "arch": {"name": "arm", "xlen": "32"},
            "test-ins": "add r1,r1,r1",
            "isa-state": {}
        }
        with self.assertRaises(ValueError):
            RISCV(json_data, "template.S")


class TestIntegration(unittest.TestCase):
    """集成测试。"""

    def test_end_to_end_generation(self):
        """测试端到端生成流程。"""
        import tempfile
        import shutil

        # 创建临时输出目录
        with tempfile.TemporaryDirectory() as tmpdir:
            json_data = load_json_spec("resource/example.json")
            from main import process_test_cases

            generated_files = process_test_cases(
                json_data,
                "resource/riscv/template.S",
                tmpdir
            )

            self.assertEqual(len(generated_files), 1)
            self.assertTrue(Path(generated_files[0]).exists())

            # 验证生成的文件内容
            with open(generated_files[0], 'r') as f:
                content = f.read()
                self.assertIn("add x1,x1,x1", content)
                self.assertIn("0x00000001", content)  # x1 的值


def run_tests():
    """运行所有测试。"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestValue))
    suite.addTests(loader.loadTestsFromTestCase(TestFilenameGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestJSONParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestRISCVClass))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 返回退出码
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
