import argparse

from sqlalchemy import select

from core.database import SessionLocal
from core.models.user import AppUser
from core.utils.security import hash_password


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    args = p.parse_args()

    db = SessionLocal()
    try:
        user = db.execute(select(AppUser).where(AppUser.email == args.email.lower())).scalar_one_or_none()
        if not user:
            print(f"Пользователь {args.email} не найден")
            return
        user.password_hash = hash_password(args.password)
        db.commit()
        print(f"Пароль обновлён для {args.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()