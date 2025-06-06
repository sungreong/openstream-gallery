from cryptography.fernet import Fernet
import os
import base64


class CryptoService:
    def __init__(self):
        # 환경변수에서 암호화 키 가져오기, 없으면 생성
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if not encryption_key:
            # 개발용 기본 키 (실제 운영에서는 반드시 환경변수로 설정)
            encryption_key = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="

        self.fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)

    def encrypt(self, data: str) -> str:
        """문자열을 암호화"""
        if not data:
            return ""
        encrypted_data = self.fernet.encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """암호화된 문자열을 복호화"""
        if not encrypted_data:
            return ""
        try:
            decoded_data = base64.b64decode(encrypted_data.encode())
            decrypted_data = self.fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception:
            return ""

    @staticmethod
    def generate_key() -> str:
        """새로운 암호화 키 생성"""
        return Fernet.generate_key().decode()
