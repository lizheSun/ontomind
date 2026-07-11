"""Fernet 加密模块 — 用于数据源密码等敏感字段的静态加密。

支持通过环境变量 FERNET_KEY 提供密钥；逗号分隔的多密钥自动切换到 MultiFernet
用于零停机轮换（第一个 key = 加密使用，其余 key = 兼容解密）。

安全约定：
1. 密钥来自环境变量，NEVER 硬编码。
2. 若 FERNET_KEY 缺失，模块级 ENCRYPTION_DISABLED=True；调用方（如 dp_data_source_service）
   应在写入路径上检查此标志并抛出 BusinessException。
3. 读取路径（decrypt 已有 ciphertext）不受 ENCRYPTION_DISABLED 影响 —— 但缺少 key
   会导致 decrypt 抛 InvalidToken。
"""
from __future__ import annotations

import os
from typing import Optional

from cryptography.fernet import Fernet, MultiFernet, InvalidToken
from loguru import logger

_ENV_VAR = "FERNET_KEY"

_fernet: Optional[MultiFernet] = None
ENCRYPTION_DISABLED: bool = True


def _load() -> None:
    """从环境读取密钥并初始化 (Multi)Fernet；模块加载时和轮换后都会调用。"""
    global _fernet, ENCRYPTION_DISABLED
    raw = os.environ.get(_ENV_VAR, "").strip()
    if not raw:
        _fernet = None
        ENCRYPTION_DISABLED = True
        logger.error(
            "[加密未启用] 环境变量 FERNET_KEY 未设置，数据源密码写入将被拒绝。"
            "生成密钥：python backend/scripts/gen_fernet.py"
        )
        return
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    try:
        fernets = [Fernet(k.encode()) for k in keys]
    except (ValueError, Exception) as e:  # invalid base64/length
        _fernet = None
        ENCRYPTION_DISABLED = True
        logger.error(f"[加密未启用] FERNET_KEY 格式不正确（{type(e).__name__}: {e}）")
        return
    _fernet = MultiFernet(fernets)
    ENCRYPTION_DISABLED = False
    logger.info(f"[加密已启用] Fernet 密钥 {len(fernets)} 把已就绪")


def encrypt(plaintext: str) -> str:
    """加密明文 → base64 字符串。ENCRYPTION_DISABLED 时抛 RuntimeError。"""
    if _fernet is None:
        raise RuntimeError(
            "FERNET_KEY 未配置，无法加密。请先设置环境变量后重启后端。"
        )
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(token: str) -> str:
    """解密 base64 密文 → 原文。密钥缺失或 token 损坏时抛 InvalidToken。"""
    if _fernet is None:
        raise InvalidToken("FERNET_KEY 未配置，无法解密")
    return _fernet.decrypt(token.encode("ascii")).decode("utf-8")


def rotate(token: str) -> str:
    """使用当前主 key 重新加密旧 token（用于密钥轮换后升级历史密文）。"""
    if _fernet is None:
        raise RuntimeError("FERNET_KEY 未配置，无法轮换")
    return _fernet.rotate(token.encode("ascii")).decode("ascii")


def require_key_or_raise() -> None:
    """调用点显式检查：加密未启用时抛 RuntimeError，供 service 层转换成 BusinessException。"""
    if ENCRYPTION_DISABLED:
        raise RuntimeError(
            "服务器加密未配置：请设置 FERNET_KEY 后再执行敏感字段写入。"
        )


# 模块加载时立即初始化
_load()
