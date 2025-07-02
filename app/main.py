import time
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.fetcher import fetch_events
from app.db import insert_events
from app.api import router as api_router


init_db()


def fetch_and_store_loop():
    while True:
        events, limit, remaining, reset_time = fetch_events()
        insert_events(events)
        print(f"Inserted {len(events)} events. Rate limit: {remaining}/{limit}.")

        # Primary rate limit
        seconds_left = reset_time - time.time()
        if remaining > 0 and seconds_left > 0:
            period = seconds_left / remaining
            print(
                f"Requests left: {remaining}. Sleep {period:.2f} seconds before next request."
            )
            time.sleep(period)
        elif remaining == 0:
            print(f"Quota used up. Waiting {seconds_left:.2f} seconds for reset.")
            time.sleep(max(seconds_left, 1))
        else:
            print("Something weird happened, sleeping 1 second.")
            time.sleep(1)


@asynccontextmanager
async def lifespan(_: FastAPI):
    thread = threading.Thread(target=fetch_and_store_loop, daemon=True)
    thread.start()
    print("Background fetcher started.")
    yield
    print("Background fetcher shutting down...")


app = FastAPI(lifespan=lifespan)
app.include_router(api_router)
