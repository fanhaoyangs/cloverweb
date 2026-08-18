#!/usr/bin/env python3
"""
parse_env.py - 把 .env 文件解析成可被 bash 使用的 export 语句
用法: python3 parse_env.py <env_file> [quoted|unquoted]
  quoted (默认): 输出 export KEY='val'（用于 eval）
  unquoted:      输出 export KEY=val（用于 env 透传，避免引号当字符串）
"""
import sys
from pathlib import Path
from dotenv import dotenv_values


def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: parse_env.py <env_file> [quoted|unquoted]", file=sys.stderr)
        sys.exit(1)
    env_path = Path(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) == 3 else "quoted"
    if mode not in ("quoted", "unquoted"):
        print(f"ERROR: mode 必须是 quoted 或 unquoted，收到 {mode!r}", file=sys.stderr)
        sys.exit(1)
    if not env_path.exists():
        print(f"ERROR: {env_path} 不存在", file=sys.stderr)
        sys.exit(1)
    for k, v in dotenv_values(env_path).items():
        if v is None:
            continue
        if mode == "quoted":
            # bash 单引号字符串内不允许 '，所以 'foo'\''bar' 表示 "foo'bar"
            safe = v.replace("'", "'\\''")
            print(f"export {k}='{safe}'")
        else:
            # unquoted：直接输出，但用 \ 转义特殊字符
            # 注意：必须 set +H 关历史扩展，! 才不会触发 bash 扩展
            safe = v.replace("\\", "\\\\").replace(" ", "\\ ").replace("'", "\\'")
            print(f"export {k}={safe}")


if __name__ == "__main__":
    main()
