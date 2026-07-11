#!/usr/bin/env python3
"""生成一把新的 Fernet 密钥，直接打印到 stdout。

用法：
    python backend/scripts/gen_fernet.py
    # 输出示例：XXaBcD...（44 字符 urlsafe base64）
    # 把这行塞进 backend/.env 的 FERNET_KEY=

生成多个用于轮换：
    python backend/scripts/gen_fernet.py 3
    # 输出 3 行；把第一行作为 FERNET_KEY 的主 key，用逗号分隔加入历史 key
"""
import sys
from cryptography.fernet import Fernet


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    for _ in range(n):
        print(Fernet.generate_key().decode("ascii"))


if __name__ == "__main__":
    main()
