import time

from app.db import SessionLocal
from app.ingestion import poll_all


def main():
    while True:
        db = SessionLocal()
        try:
            poll_all(db)
        except Exception as exc:
            print("worker error", exc)
        finally:
            db.close()
        time.sleep(30)


if __name__ == "__main__":
    main()
