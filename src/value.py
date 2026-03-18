class Value:
    def __init__(self, exp: str):
        self.bits = 0
        self.mask = 0
        self.len = 0
        self._parse(exp)

    def _parse(self, exp: str):
        """解析表达式，支持格式：
        - 十进制: "42"
        - 十六进制: "64'h0000_0000_0000_0010", "32'h0000_0001"
        - 二进制: "32'b0000_0001"
        - 带掩码: "{64'h0000_0000_0000_0000, 64'b...}"
        """
        exp = str(exp).strip().replace(" ", "").replace("_", "")
        has_mask = False

        # 处理带掩码的格式 {value, mask}
        if exp.startswith("{") and exp.endswith("}"):
            inner = exp[1:-1]
            parts = inner.split(",")
            if len(parts) == 2:
                has_mask = True
                # 先解析值，保存位宽
                value_len = self._extract_bitlen(parts[0])
                self._parse_value(parts[0], is_mask=False)

                # 检查掩码位宽是否一致
                mask_len = self._extract_bitlen(parts[1])
                if value_len != mask_len:
                    raise ValueError(
                        f'ValueError: "{{{{{parts[0]}, {parts[1]}}}}}" 值位宽 {value_len} 与掩码位宽 {mask_len} 不一致'
                    )
                self._parse_value(parts[1], is_mask=True)
            else:
                self._parse_value(inner, is_mask=False)
        else:
            self._parse_value(exp, is_mask=False)

        # 没有显式指定 mask 时，默认为全 1
        if not has_mask:
            self.mask = (1 << self.len) - 1

    def _extract_bitlen(self, exp: str) -> int:
        """提取表达式的位宽"""
        exp = exp.strip()
        if "'" in exp:
            width_part, _ = exp.split("'", 1)
            try:
                return int(width_part)
            except ValueError:
                raise ValueError(f"无效的位宽语法: '{exp}'")
        raise ValueError(f"缺少位宽前缀: '{exp}'，正确格式如 '32'h...'")

    def _parse_value(self, exp: str, is_mask: bool = False):
        """解析单个值"""
        if not exp:
            return

        # 解析位宽和进制
        if "'" in exp:
            width_part, value_part = exp.split("'", 1)
            self.len = int(width_part)
        else:
            raise ValueError(f"缺少位宽前缀: '{exp}'，正确格式如 '32'h...'")

        # 根据前缀解析数值
        if value_part.startswith('h') or value_part.startswith('H'):
            value = int(value_part[1:], 16) if len(value_part) > 1 else 0
        elif value_part.startswith('b') or value_part.startswith('B'):
            value = int(value_part[1:], 2) if len(value_part) > 1 else 0
        elif value_part.startswith('d') or value_part.startswith('D'):
            value = int(value_part[1:], 10) if len(value_part) > 1 else 0
        else:
            raise ValueError(f"无效的进制前缀: '{exp}'，支持的前缀为 'h'(十六进制), 'b'(二进制), 'd'(十进制)")

        # 检查实际位宽是否超过声明的位宽
        actual_bitlen = value.bit_length()
        if actual_bitlen > self.len:
            raise ValueError(
                f'ValueError: "{exp}" 值 {value:#x} 需要 {actual_bitlen} 位，但声明的位宽为 {self.len} 位'
            )

        if is_mask:
            self.mask = value
        else:
            self.bits = value

    def to_hex(self) -> str:
        """转换为十六进制字符串"""
        # 应用掩码
        if self.mask:
            masked_value = self.bits & self.mask
        else:
            masked_value = self.bits

        # 根据位宽输出
        if self.len == 64:
            return f"0x{masked_value:016x}"
        elif self.len == 32:
            return f"0x{masked_value:08x}"
        elif self.len == 16:
            return f"0x{masked_value:04x}"
        elif self.len == 8:
            return f"0x{masked_value:02x}"
        else:
            # 其他位宽，计算需要的字符数
            hex_chars = (self.len + 3) // 4
            return f"0x{masked_value:0{hex_chars}x}"

    def get_mask(self) -> int:
        """获取掩码值"""
        return self.mask

    def __eq__(self, other):
        if isinstance(other, Value):
            return self.bits == other.bits and self.mask == other.mask
        return False

    def __repr__(self):
        if self.mask:
            return f"Value(bits={self.bits:#x}, mask={self.mask:#x})"
        return f"Value({self.bits:#x})"


# test
import pytest

class TestValue:
    """
    输入格式示例:
    - "64'h0000_0000_0000_0010"
    - "32'h0000_0001"
    - "32'b0000_0001"
    - "{64'h0000_0000_0000_0000, 64'b0000_0000_0000_0000_0000_0000_0000_0000_0000_0000_0000_0000_0000_0000_0000_0000}" 第1个是值，第2个是mask掩码
    """

	#========功能测试=======
    def test_64bit_hex(self):
        v = Value("64'h0000_0000_0000_0010")
        assert v.bits == 16
        assert v.len == 64
        assert v.mask == 2**64-1
        assert v.to_hex() == "0x0000000000000010"


    def test_32bit_binary(self):
        v = Value("32'b0000_0001")
        assert v.bits == 1
        assert v.len == 32
        assert v.mask == 2**32-1
        assert v.to_hex() == "0x00000001"

    def test_decimal(self):
        v = Value("32'd42")
        assert v.bits == 42
        assert v.len == 32
        assert v.mask == 2**32-1

    def test_with_mask(self):
        v = Value("{64'hffff_ffff_ffff_ffff, 64'h0000_0000_0000_00ff}")
        assert v.bits == 0xffffffffffffffff
        assert v.len == 64
        assert v.mask == 0xff
        # 应用掩码后应该是0xff
        assert v.to_hex() == "0x00000000000000ff"

    def test_with_binary_mask(self):
        v = Value("{64'hffff_ffff_ffff_ffff, 64'b0000_0000_0000_0000_0000_0000_0000_0000_0000_0000_0000_0000_0000_0000_1111_1111}")
        assert v.bits == 0xffffffffffffffff
        assert v.len == 64
        assert v.mask == 0xff
        assert v.to_hex() == "0x00000000000000ff"

    def test_equality(self):
        v1 = Value("32'h0000_0001")
        v2 = Value("32'b0000_0001")
        assert v1 == v2
        # 检查 v1 的属性
        assert v1.bits == 1
        assert v1.len == 32
        assert v1.mask == 2**32-1
        # 检查 v2 的属性
        assert v2.bits == 1
        assert v2.len == 32
        assert v2.mask == 2**32-1

	#边界测试
    def test_length_error(self):
        with pytest.raises(ValueError) as excinfo:
            Value("{32'b10,16'b1}")
        assert '"{{32\'b10, 16\'b1}}"' in str(excinfo.value)
        assert "32" in str(excinfo.value)
        assert "16" in str(excinfo.value)

    def test_2bit_hex(self):
        with pytest.raises(ValueError) as excinfo:
            Value("2'h1000_0001")
        assert '"2\'h' in str(excinfo.value)
        assert "0x10000001" in str(excinfo.value)
        assert "需要 29 位，但声明的位宽为 2 位" in str(excinfo.value)
