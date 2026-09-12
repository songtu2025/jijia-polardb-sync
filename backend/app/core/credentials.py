from cryptography.fernet import Fernet, InvalidToken

from backend.app.core.errors import ApiError


class CredentialCipher:
    """加密和解密积加账号凭证，数据库只保存密文。"""

    def __init__(self, key: str) -> None:
        if not key:
            raise ApiError(503, "CREDENTIAL_KEY_MISSING", "尚未配置凭证加密密钥")
        try:
            self._fernet = Fernet(key.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as error:
            raise ApiError(503, "CREDENTIAL_KEY_INVALID", "凭证加密密钥格式不正确") from error

    def encrypt(self, value: str) -> str:
        """加密单个凭证字段。"""
        return self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        """解密单个凭证字段，密文损坏时不泄露原始内容。"""
        try:
            return self._fernet.decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError, UnicodeEncodeError) as error:
            raise ApiError(500, "CREDENTIAL_DECRYPT_FAILED", "账号凭证无法解密") from error
