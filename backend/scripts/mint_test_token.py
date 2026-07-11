"""Mint a JWT for testing routers with curl. Usage: python mint_test_token.py [username]."""
import sys

from app.core.security import create_access_token
from app.db.models.user_model import User
from app.db.session import SessionLocal


def main() -> None:
    username = sys.argv[1] if len(sys.argv) > 1 else "admin"
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == username).first()
        if u is None:
            print(f"user {username} not found", file=sys.stderr)
            sys.exit(1)
        token = create_access_token({"sub": u.username, "user_id": u.id})
        print(token)
    finally:
        db.close()


if __name__ == "__main__":
    main()
