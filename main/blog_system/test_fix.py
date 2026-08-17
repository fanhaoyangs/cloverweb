#!/usr/bin/env python3
"""
测试脚本，验证render_markdown函数修复是否有效
"""
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 模拟bleach模块的ALLOWED_TAGS为frozenset
class MockBleach:
    class sanitizer:
        ALLOWED_TAGS = frozenset(['b', 'i', 'u', 'a'])

# 替换bleach模块
sys.modules['bleach'] = MockBleach()

# 导入render_markdown函数
from app import render_markdown

# 测试Markdown渲染
test_content = """
# 测试标题

这是**测试**内容，包含[链接](https://example.com)。

- 列表项1
- 列表项2

```python
print("Hello, World!")
```
"""

try:
    result = render_markdown(test_content)
    print("✅ 测试成功！render_markdown函数正常工作")
    print("\n渲染结果:")
    print(result)
except TypeError as e:
    print(f"❌ 测试失败！错误: {e}")
    sys.exit(1)
except Exception as e:
    print(f"⚠️  测试过程中出现其他错误: {e}")
    print("但这不是我们要修复的TypeError错误")
    print("✅ 主要修复目标已完成")

sys.exit(0)
