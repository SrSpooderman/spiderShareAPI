import bcrypt


class PasswordHasher:
    def hash_password(self, plain_password: str) -> str:
        password_bytes = plain_password.encode("utf-8")
        salt = bcrypt.gensalt()

        return bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        password_bytes = plain_password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")

        try:
            return bcrypt.checkpw(password_bytes, hash_bytes)
        except ValueError:
            return False
