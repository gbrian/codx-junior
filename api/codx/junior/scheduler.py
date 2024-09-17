import logging

from apscheduler.schedulers.background import BackgroundScheduler
# The "apscheduler." prefix is hard coded
scheduler = BackgroundScheduler()

SCHEDULED_WORKS = []
ON_SCHEDULE = False
def on_schedule():
    global ON_SCHEDULE
    global SCHEDULED_WORKS
    if ON_SCHEDULE:
      return
    ON_SCHEDULE = True
    for work in SCHEDULED_WORKS:
        try:
            work()
        except Exception as ex:
            pass
    ON_SCHEDULE = False

scheduler.add_job(on_schedule, 'interval', seconds=3)
scheduler.start()

def add_work(work):
    logging.info(f"Adding job")
    SCHEDULED_WORKS.append(work)
