# test
import os
import pytest
from main import main


class TestMain:
    def test_sanitize_filename(self):
        """测试文件名清理功能"""
        from main import sanitize_filename

        assert sanitize_filename("rv32d") == "rv32d"
        assert sanitize_filename("add x1,x1,x1") == "add_x1_x1_x1"
        assert sanitize_filename("test,with:commas") == "test_with_commas"
        assert sanitize_filename("test with spaces") == "test_with_spaces"
        # 测试括号被替换为下划线
        assert sanitize_filename("test(a,b)") == "test_a_b"
        # 测试多个连续下划线合并
        assert sanitize_filename("test___name") == "test_name"
        # 测试首尾下划线去除
        assert sanitize_filename("_test_") == "test"
        # 测试长度截断
        long_name = "a" * 300
        assert len(sanitize_filename(long_name, max_length=100)) == 100

    def test_generate_output_filename(self):
        """测试输出文件名生成"""
        from main import generate_output_filename

        assert (
            generate_output_filename("rv32d", "add x1,x1,x1") == "rv32d_add_x1_x1_x1.S"
        )
        assert generate_output_filename("rv64i", "lw x10,0(x1)") == "rv64i_lw_x10_0_x1.S"
        # 测试带 ret_val 的情况，括号被替换为下划线
        assert generate_output_filename("rv32d", "wfi", "Illegal_Instruction(())") == "rv32d_wfi_Illegal_Instruction.S"
        assert generate_output_filename("rv32d", "wfi", "Enter_Wait(WaitReason::zWAIT_WFI(EnumMember_member:0))") == "rv32d_wfi_Enter_Wait_WaitReason_zWAIT_WFI_EnumMember_member_0.S"

    def test_main_with_args(self):
        """测试main函数传入参数列表"""
        import tempfile
        import shutil

        # 创建临时目录和文件
        tmpdir = tempfile.mkdtemp()
        try:
            # 创建模板文件
            template_path = os.path.join(tmpdir, "template.S")
            with open(template_path, "w") as f:
                f.write("${test_ins}\nli x1, ${X1_VAL}\n")

            # 创建JSON文件
            json_path = os.path.join(tmpdir, "test.json")
            with open(json_path, "w") as f:
                f.write("""{
    "gen": [
        {
            "arch": {
                "name": "riscv",
                "pretty-name": "test",
                "xlen": 32
            },
            "test-ins": "add x1,x1,x1",
            "test-ins-encdec": "32'h0030_8033",
            "isa-state": {
                "x1": "32'd1"
            }
        }
    ]
}""")

            # 创建输出目录
            output_dir = os.path.join(tmpdir, "output")

            # 调用main函数，传入参数列表
            main(["--template", template_path, "--json", json_path, "--output-dir", output_dir])

            # 验证文件生成
            output_file = os.path.join(output_dir, "test_add_x1_x1_x1.S")
            assert os.path.exists(output_file)
            with open(output_file, "r") as f:
                content = f.read()
                assert ".insn 0x00308033" in content
                assert "li x1, 0x00000001" in content
        finally:
            shutil.rmtree(tmpdir)

    def test_file_exists_without_force(self):
        """测试文件已存在且没有 -f 参数时退出码 255"""
        import tempfile
        import shutil

        tmpdir = tempfile.mkdtemp()
        try:
            # 创建模板文件
            template_path = os.path.join(tmpdir, "template.S")
            with open(template_path, "w") as f:
                f.write("${test_ins}\n")

            # 创建JSON文件
            json_path = os.path.join(tmpdir, "test.json")
            with open(json_path, "w") as f:
                f.write("""{
    "gen": [
        {
            "arch": {
                "name": "riscv",
                "pretty-name": "test",
                "xlen": 32
            },
            "test-ins": "add x1,x1,x1",
            "test-ins-encdec": "32'h0030_8033",
            "isa-state": {}
        }
    ]
}""")

            # 创建输出目录
            output_dir = os.path.join(tmpdir, "output")

            # 第一次运行应该成功
            main(["--template", template_path, "--json", json_path, "--output-dir", output_dir])

            # 第二次运行应该因文件已存在而退出（返回 255）
            with pytest.raises(SystemExit) as exc_info:
                main(["--template", template_path, "--json", json_path, "--output-dir", output_dir])
            assert exc_info.value.code == 255
        finally:
            shutil.rmtree(tmpdir)

    def test_file_exists_with_force(self):
        """测试使用 -f 参数强制覆盖已存在的文件"""
        import tempfile
        import shutil

        tmpdir = tempfile.mkdtemp()
        try:
            # 创建模板文件
            template_path = os.path.join(tmpdir, "template.S")
            with open(template_path, "w") as f:
                f.write("${test_ins}\nNEW_CONTENT\n")

            # 创建JSON文件
            json_path = os.path.join(tmpdir, "test.json")
            with open(json_path, "w") as f:
                f.write("""{
    "gen": [
        {
            "arch": {
                "name": "riscv",
                "pretty-name": "test",
                "xlen": 32
            },
            "test-ins": "add x1,x1,x1",
            "test-ins-encdec": "32'h0030_8033",
            "isa-state": {}
        }
    ]
}""")

            # 创建输出目录和已存在的文件
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(output_dir)
            existing_file = os.path.join(output_dir, "test_add_x1_x1_x1.S")
            with open(existing_file, "w") as f:
                f.write("OLD_CONTENT")

            # 使用 -f 参数应该覆盖
            main(["--template", template_path, "--json", json_path, "--output-dir", output_dir, "-f"])

            # 验证文件已被覆盖
            with open(existing_file, "r") as f:
                content = f.read()
                assert "NEW_CONTENT" in content
                assert "OLD_CONTENT" not in content
        finally:
            shutil.rmtree(tmpdir)

    def test_multiple_json_files(self):
        """测试多次使用 --json 参数处理多个文件"""
        import tempfile
        import shutil

        tmpdir = tempfile.mkdtemp()
        try:
            # 创建模板文件
            template_path = os.path.join(tmpdir, "template.S")
            with open(template_path, "w") as f:
                f.write("${test_ins}\n")

            # 创建第一个JSON文件
            json1_path = os.path.join(tmpdir, "test1.json")
            with open(json1_path, "w") as f:
                f.write("""{
    "gen": [
        {
            "arch": {
                "name": "riscv",
                "pretty-name": "rv32i",
                "xlen": 32
            },
            "test-ins": "add x1,x1,x1",
            "test-ins-encdec": "32'h0030_8033",
            "isa-state": {}
        }
    ]
}""")

            # 创建第二个JSON文件
            json2_path = os.path.join(tmpdir, "test2.json")
            with open(json2_path, "w") as f:
                f.write("""{
    "gen": [
        {
            "arch": {
                "name": "riscv",
                "pretty-name": "rv64i",
                "xlen": 64
            },
            "test-ins": "sub x2,x2,x2",
            "test-ins-encdec": "32'h4030_8133",
            "isa-state": {}
        }
    ]
}""")

            # 创建输出目录
            output_dir = os.path.join(tmpdir, "output")

            # 调用main函数，使用多个 --json 参数
            main(["--template", template_path, "--json", json1_path, "--json", json2_path, "--output-dir", output_dir])

            # 验证两个文件都生成了
            output_file1 = os.path.join(output_dir, "rv32i_add_x1_x1_x1.S")
            output_file2 = os.path.join(output_dir, "rv64i_sub_x2_x2_x2.S")
            assert os.path.exists(output_file1)
            assert os.path.exists(output_file2)
        finally:
            shutil.rmtree(tmpdir)

    def test_json_dir_mode(self):
        """测试 --json-dir 批量处理目录中所有JSON"""
        import tempfile
        import shutil

        tmpdir = tempfile.mkdtemp()
        try:
            # 创建模板文件
            template_path = os.path.join(tmpdir, "template.S")
            with open(template_path, "w") as f:
                f.write("${test_ins}\n")

            # 在目录中创建多个JSON文件
            json_dir = os.path.join(tmpdir, "configs")
            os.makedirs(json_dir)

            json1_path = os.path.join(json_dir, "test1.json")
            with open(json1_path, "w") as f:
                f.write("""{
    "gen": [
        {
            "arch": {
                "name": "riscv",
                "pretty-name": "rv32i",
                "xlen": 32
            },
            "test-ins": "add x1,x1,x1",
            "test-ins-encdec": "32'h0030_8033",
            "isa-state": {}
        }
    ]
}""")

            json2_path = os.path.join(json_dir, "test2.json")
            with open(json2_path, "w") as f:
                f.write("""{
    "gen": [
        {
            "arch": {
                "name": "riscv",
                "pretty-name": "rv64i",
                "xlen": 64
            },
            "test-ins": "sub x2,x2,x2",
            "test-ins-encdec": "32'h4030_8133",
            "isa-state": {}
        }
    ]
}""")

            # 创建一个非JSON文件，应该被忽略
            with open(os.path.join(json_dir, "readme.txt"), "w") as f:
                f.write("not a json file")

            # 创建输出目录
            output_dir = os.path.join(tmpdir, "output")

            # 调用main函数，使用 --json-dir
            main(["--template", template_path, "--json-dir", json_dir, "--output-dir", output_dir])

            # 验证文件生成
            output_file1 = os.path.join(output_dir, "rv32i_add_x1_x1_x1.S")
            output_file2 = os.path.join(output_dir, "rv64i_sub_x2_x2_x2.S")
            assert os.path.exists(output_file1)
            assert os.path.exists(output_file2)
        finally:
            shutil.rmtree(tmpdir)

    def test_json_and_json_dir_combined(self):
        """测试同时使用 --json 和 --json-dir"""
        import tempfile
        import shutil

        tmpdir = tempfile.mkdtemp()
        try:
            # 创建模板文件
            template_path = os.path.join(tmpdir, "template.S")
            with open(template_path, "w") as f:
                f.write("${test_ins}\n")

            # 创建单个JSON文件
            json1_path = os.path.join(tmpdir, "single.json")
            with open(json1_path, "w") as f:
                f.write("""{
    "gen": [
        {
            "arch": {
                "name": "riscv",
                "pretty-name": "single",
                "xlen": 32
            },
            "test-ins": "and x1,x1,x1",
            "test-ins-encdec": "32'h0030_7033",
            "isa-state": {}
        }
    ]
}""")

            # 创建JSON目录
            json_dir = os.path.join(tmpdir, "configs")
            os.makedirs(json_dir)

            json2_path = os.path.join(json_dir, "dir1.json")
            with open(json2_path, "w") as f:
                f.write("""{
    "gen": [
        {
            "arch": {
                "name": "riscv",
                "pretty-name": "dir1",
                "xlen": 32
            },
            "test-ins": "or x2,x2,x2",
            "test-ins-encdec": "32'h4031_6133",
            "isa-state": {}
        }
    ]
}""")

            json3_path = os.path.join(json_dir, "dir2.json")
            with open(json3_path, "w") as f:
                f.write("""{
    "gen": [
        {
            "arch": {
                "name": "riscv",
                "pretty-name": "dir2",
                "xlen": 32
            },
            "test-ins": "xor x3,x3,x3",
            "test-ins-encdec": "32'h4032_4233",
            "isa-state": {}
        }
    ]
}""")

            # 创建输出目录
            output_dir = os.path.join(tmpdir, "output")

            # 同时使用 --json 和 --json-dir
            main(["--template", template_path, "--json", json1_path, "--json-dir", json_dir, "--output-dir", output_dir])

            # 验证所有文件都生成了
            output_file1 = os.path.join(output_dir, "single_and_x1_x1_x1.S")
            output_file2 = os.path.join(output_dir, "dir1_or_x2_x2_x2.S")
            output_file3 = os.path.join(output_dir, "dir2_xor_x3_x3_x3.S")
            assert os.path.exists(output_file1)
            assert os.path.exists(output_file2)
            assert os.path.exists(output_file3)
        finally:
            shutil.rmtree(tmpdir)

    def test_duplicate_output_filename_same_file(self):
        """测试同一JSON文件内的重复文件名自动添加后缀"""
        import tempfile
        import shutil

        tmpdir = tempfile.mkdtemp()
        try:
            # 创建模板文件
            template_path = os.path.join(tmpdir, "template.S")
            with open(template_path, "w") as f:
                f.write("${test_ins}\n")

            # 创建JSON文件，包含两个会产生相同输出文件名的条目
            json_path = os.path.join(tmpdir, "test.json")
            with open(json_path, "w") as f:
                f.write("""{
    "gen": [
        {
            "arch": {
                "name": "riscv",
                "pretty-name": "rv32d",
                "xlen": 32
            },
            "test-ins": "wfi",
            "test-ins-encdec": "32'h1050_0073",
            "isa-state": {
                "cur_privilege": "User"
            }
        },
        {
            "arch": {
                "name": "riscv",
                "pretty-name": "rv32d",
                "xlen": 32
            },
            "test-ins": "wfi",
            "test-ins-encdec": "32'h1050_0073",
            "isa-state": {
                "cur_privilege": "Supervisor"
            }
        },
        {
            "arch": {
                "name": "riscv",
                "pretty-name": "rv32d",
                "xlen": 32
            },
            "test-ins": "wfi",
            "test-ins-encdec": "32'h1050_0073",
            "isa-state": {
                "cur_privilege": "Machine"
            }
        }
    ]
}""")

            # 创建输出目录
            output_dir = os.path.join(tmpdir, "output")

            # 应该自动添加数字后缀，不报错
            main(["--template", template_path, "--json", json_path, "--output-dir", output_dir])

            # 验证生成了三个文件，带数字后缀
            output_file1 = os.path.join(output_dir, "rv32d_wfi.S")
            output_file2 = os.path.join(output_dir, "rv32d_wfi_2.S")
            output_file3 = os.path.join(output_dir, "rv32d_wfi_3.S")
            assert os.path.exists(output_file1)
            assert os.path.exists(output_file2)
            assert os.path.exists(output_file3)
        finally:
            shutil.rmtree(tmpdir)

    def test_duplicate_output_filename_multiple_files(self):
        """测试多个JSON文件之间的输出文件名冲突"""
        import tempfile
        import shutil

        tmpdir = tempfile.mkdtemp()
        try:
            # 创建模板文件
            template_path = os.path.join(tmpdir, "template.S")
            with open(template_path, "w") as f:
                f.write("${test_ins}\n")

            # 创建第一个JSON文件
            json1_path = os.path.join(tmpdir, "test1.json")
            with open(json1_path, "w") as f:
                f.write("""{
    "gen": [
        {
            "arch": {
                "name": "riscv",
                "pretty-name": "rv32i",
                "xlen": 32
            },
            "test-ins": "add x1,x1,x1",
            "test-ins-encdec": "32'h0030_8033",
            "isa-state": {}
        }
    ]
}""")

            # 创建第二个JSON文件，产生相同的输出文件名
            json2_path = os.path.join(tmpdir, "test2.json")
            with open(json2_path, "w") as f:
                f.write("""{
    "gen": [
        {
            "arch": {
                "name": "riscv",
                "pretty-name": "rv32i",
                "xlen": 32
            },
            "test-ins": "add x1,x1,x1",
            "test-ins-encdec": "32'h0030_8033",
            "isa-state": {}
        }
    ]
}""")

            # 创建输出目录
            output_dir = os.path.join(tmpdir, "output")

            # 应该检测到文件名冲突并退出
            with pytest.raises(SystemExit) as exc_info:
                main(["--template", template_path, "--json", json1_path, "--json", json2_path, "--output-dir", output_dir])
            assert exc_info.value.code == 255
        finally:
            shutil.rmtree(tmpdir)

    def test_empty_gen_array(self):
        """测试空 gen 数组的 JSON 文件被忽略"""
        import tempfile
        import shutil

        tmpdir = tempfile.mkdtemp()
        try:
            # 创建模板文件
            template_path = os.path.join(tmpdir, "template.S")
            with open(template_path, "w") as f:
                f.write("${test_ins}\n")

            # 创建空 gen 数组的 JSON 文件
            json_path = os.path.join(tmpdir, "empty.json")
            with open(json_path, "w") as f:
                f.write('{"gen": []}')

            # 创建输出目录
            output_dir = os.path.join(tmpdir, "output")

            # 应该成功运行，不生成任何文件
            main(["--template", template_path, "--json", json_path, "--output-dir", output_dir])

            # 验证没有生成任何文件
            assert len(os.listdir(output_dir)) == 0
        finally:
            shutil.rmtree(tmpdir)

    def test_empty_json_object(self):
        """测试空 JSON 对象被忽略"""
        import tempfile
        import shutil

        tmpdir = tempfile.mkdtemp()
        try:
            # 创建模板文件
            template_path = os.path.join(tmpdir, "template.S")
            with open(template_path, "w") as f:
                f.write("${test_ins}\n")

            # 创建空 JSON 对象
            json_path = os.path.join(tmpdir, "empty.json")
            with open(json_path, "w") as f:
                f.write('{}')

            # 创建输出目录
            output_dir = os.path.join(tmpdir, "output")

            # 应该成功运行，不生成任何文件
            main(["--template", template_path, "--json", json_path, "--output-dir", output_dir])

            # 验证没有生成任何文件
            assert len(os.listdir(output_dir)) == 0
        finally:
            shutil.rmtree(tmpdir)

