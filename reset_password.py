import sys
import argparse
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import SessionLocal
from app.core.security import get_password_hash
from app.api.staff import generate_compliant_temp_password
from app.models.user import User
from app.models.refresh_token import RefreshToken


def main():
    parser = argparse.ArgumentParser(description="Reset user password to a temporary password (CLI).")
    parser.add_argument("email", nargs="?", help="Email of the user (e.g. owner) to reset")
    args = parser.parse_args()

    email = args.email
    if not email:
        email = input("Enter user email to reset: ").strip()

    if not email:
        print("Error: Email is required.")
        sys.exit(1)

    db: Session = SessionLocal()
    try:
        user = db.execute(select(User).where(User.email == email.lower().strip())).scalar_one_or_none()
        if not user:
            print(f"Error: User with email '{email}' not found.")
            sys.exit(1)

        temp_password = generate_compliant_temp_password(16)
        now = datetime.now(timezone.utc)
        user.password_hash = get_password_hash(temp_password)
        user.must_change_password = True
        user.temp_password_expires_at = now + timedelta(hours=72)
        user.token_version += 1

        # Invalidate active refresh tokens
        user_tokens = db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None)
            )
        ).scalars().all()
        for t in user_tokens:
            t.revoked_at = now

        db.commit()

        print(f"\nSUCCESS: Password for '{user.email}' (role: {user.role}) reset.")
        print(f"Temporary Password: {temp_password}")
        print("Note: Valid for 72 hours. The user will be required to choose a new password upon first login.\n")
    except Exception as e:
        db.rollback()
        print(f"Error resetting password: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
