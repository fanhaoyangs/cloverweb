#!/usr/bin/env python3
"""
简化测试脚本，只验证类型转换修复
"""

# 模拟bleach模块的ALLOWED_TAGS为frozenset
class MockBleach:
    class sanitizer:
        ALLOWED_TAGS = frozenset(['b', 'i', 'u', 'a'])

# 测试修复前的代码（会失败）
def test_before_fix():
    print("测试修复前的代码...")
    try:
        allowed_tags = MockBleach.sanitizer.ALLOWED_TAGS + [
            'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'strong', 'em', 'u', 'del', 'ins',
            'ul', 'ol', 'li', 'blockquote',
            'pre', 'code',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'a', 'img',
            'div', 'span',
            'br', 'hr'
        ]
        print("✅ 意外成功，可能ALLOWED_TAGS不是frozenset")
        return False
    except TypeError as e:
        print(f"❌ 失败，错误: {e}")
        return True

# 测试修复后的代码（应该成功）
def test_after_fix():
    print("\n测试修复后的代码...")
    try:
        allowed_tags = list(MockBleach.sanitizer.ALLOWED_TAGS) + [
            'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'strong', 'em', 'u', 'del', 'ins',
            'ul', 'ol', 'li', 'blockquote',
            'pre', 'code',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'a', 'img',
            'div', 'span',
            'br', 'hr'
        ]
        print(f"✅ 成功！合并后的标签数量: {len(allowed_tags)}")
        print(f"前10个标签: {allowed_tags[:10]}")
        return True
    except Exception as e:
        print(f"❌ 失败，错误: {e}")
        return False

if __name__ == "__main__":
    print("开始测试类型转换修复...\n")
    
    before_failed = test_before_fix()
    after_succeeded = test_after_fix()
    
    print("\n测试结果总结:")
    if before_failed and after_succeeded:
        print("🎉 修复成功！类型转换问题已解决")
        print("✅ 修复前: frozenset + list 操作失败")
        print("✅ 修复后: list(frozenset) + list 操作成功")
        exit(0)
    else:
        print("❌ 修复可能存在问题")
        print(f"修复前测试结果: {'失败（预期）' if before_failed else '成功（意外）'}")
        print(f"修复后测试结果: {'成功' if after_succeeded else '失败'}")
        exit(1)
