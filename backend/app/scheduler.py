from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.blocking import BlockingScheduler

from app.db import SessionLocal
from app.ingestion import poll_all
from app.models import Feed


def tick():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        feeds = db.query(Feed).filter(Feed.enabled.is_(True)).all()
        due = False
        for f in feeds:
            if not f.next_poll_at or f.next_poll_at <= now:
                due = True
                f.next_poll_at = now + timedelta(minutes=f.poll_interval_minutes or 60)
        db.commit()
        if due:
            poll_all(db)
    finally:
        db.close()


def main():
    sched = BlockingScheduler()
    sched.add_job(tick, "interval", seconds=60, id="feed-tick")
    sched.start()


if __name__ == "__main__":
    main()
