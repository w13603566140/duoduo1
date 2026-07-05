"""
解析器单元测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.parser import parse_sales_volume, parse_price, normalize_product_name


def test_parse_sales_volume():
    """测试销量文本解析"""
    test_cases = [
        ("已拼23件", 23),
        ("已拼1,230件", 1230),
        ("已拼1.2万件", 12000),
        ("已拼10万件", 100000),
        ("已拼10万+件", 100000),
        ("已拼100万+件", 1000000),
        ("已拼1.23万件", 12300),
        ("已拼0.5万件", 5000),
        ("", 0),
        (None, 0),
        ("已拼件", 0),
        ("随便什么文字", 0),
        ("已拼999999件", 999999),
    ]

    for text, expected in test_cases:
        result = parse_sales_volume(text)
        status = "PASS" if result == expected else "FAIL"
        print(f"[{status}] parse_sales_volume({text!r}) = {result} (expected {expected})")
        assert result == expected, f"Failed: {text!r} -> {result} != {expected}"

    print("\n[OK] 销量解析测试全部通过！")


def test_parse_price():
    """测试价格解析"""
    test_cases = [
        ("19.9", 19.9, "plain number"),
        ("19.9 yuan", 19.9, "number with text"),
        ("1,299.00", 1299.0, "with comma"),
        ("", None, "empty"),
        (None, None, "none"),
        ("abc", None, "no number"),
    ]

    for text, expected, desc in test_cases:
        result = parse_price(text)
        if expected is None:
            status = "PASS" if result is None else "FAIL"
            print(f"[{status}] parse_price({desc}) = {result} (expected None)")
            assert result is None, f"Failed: {desc} -> {result} != None"
        else:
            status = "PASS" if abs(result - expected) < 0.01 else "FAIL"
            print(f"[{status}] parse_price({desc}) = {result} (expected ~{expected})")
            assert abs(result - expected) < 0.01, f"Failed: {desc} -> {result} != {expected}"

    print("\n[OK] 价格解析测试全部通过！")


def test_normalize_product_name():
    """测试商品名清洗"""
    assert normalize_product_name("  莜面鱼鱼 正宗山西  ") == "莜面鱼鱼 正宗山西"
    assert normalize_product_name("") == ""
    assert normalize_product_name(None) == ""
    long_name = "x" * 600
    result = normalize_product_name(long_name)
    assert len(result) <= 512
    assert result.endswith("...")
    print("[OK] 商品名清洗测试全部通过！")


if __name__ == "__main__":
    print("=" * 60)
    print("运行解析器单元测试")
    print("=" * 60)
    test_parse_sales_volume()
    test_parse_price()
    test_normalize_product_name()
    print("\n[OK] 所有测试通过！")
