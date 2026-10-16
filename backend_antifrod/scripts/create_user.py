import argparse

from sqlalchemy import select

from core.database import SessionLocal
from core.models.user import AppUser
from core.utils.security import hash_password


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--name", default=None)
    args = p.parse_args()

    db = SessionLocal()
    try:
        if db.execute(select(AppUser).where(AppUser.email == args.email.lower())).scalar_one_or_none():
            print(f"Пользователь {args.email} уже существует")
            return
        db.add(AppUser(
            email=args.email.lower(),
            password_hash=hash_password(args.password),
            role="operator",
            full_name=args.name,
            is_active=True,
        ))
        db.commit()
        print(f"Создан operator: {args.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
