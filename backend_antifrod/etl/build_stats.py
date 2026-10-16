from services import stats_service
from core.database import SessionLocal


def main():
    db = SessionLocal()
    try:
        print(stats_service.refresh_all(db))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
