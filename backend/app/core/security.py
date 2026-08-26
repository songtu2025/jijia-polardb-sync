import hashlib
import hmac
import secrets
from datetime import UTC, datetime

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

password_hasher = PasswordHasher()
DUMMY_PASSWORD_HASH = password_hasher.hash("not-a-real-user-password")


def utc_now() -> datetime:
    """返回不带时区标记的 UTC 时间，兼容 MySQL DATETIME。"""
    return datetime.now(UTC).replace(tzinfo=None)


def normalize_email(email: str) -> str:
    """统一邮箱格式，保证查询和唯一约束使用同一值。"""
    return email.strip().lower()


def hash_password(password: str) -> str:
    """使用 Argon2id 保存密码摘要。"""
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码，非法摘要按验证失败处理。"""
    try:
        return password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def generate_token() -> str:
    """生成至少 256 位熵的一次性令牌。"""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """令牌原文只交给客户端，数据库仅保存不可逆摘要。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_matches(token: str, expected_hash: str) -> bool:
    """使用恒定时间比较令牌摘要。"""
    return hmac.compare_digest(hash_token(token), expected_hash)
