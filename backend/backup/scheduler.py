from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import requests
import os

BACKUP_API = os.getenv('BACKUP_API', 'http://localhost:8018')
CRON = os.getenv('BACKUP_CRON', '0 2 * * *')  # daily at 02:00


def trigger_backup():
    try:
        requests.post(f"{BACKUP_API}/backup/run", json={"label": "scheduled"}, timeout=60)
    except Exception:
        pass


def start_scheduler():
    sched = BackgroundScheduler(timezone="UTC")
    # Using cron string would require APScheduler CronTrigger; keep it simple: daily
    sched.add_job(trigger_backup, 'cron', hour=2, minute=0)
    sched.start()
    return sched


if __name__ == '__main__':
    start_scheduler()
    import time
    while True:
        time.sleep(3600)
