import os
import time
from typing import Any, List, Tuple

import httpx
from httpx import Headers
from dotenv import load_dotenv
from app.settings import Settings


settings = Settings()  # type: ignore
load_dotenv()

ETAG_PATH = "data/github_etag.txt"


def load_etag():
    if os.path.exists(ETAG_PATH):
        with open(ETAG_PATH, "r") as f:
            return f.read().strip()
        return None


def save_etag(etag: str):
    with open(ETAG_PATH, "w") as f:
        f.write(etag)


def parse_rate_limit_headers(headers: Headers) -> tuple[int, int, int]:
    limit = int(headers.get("x-ratelimit-limit", 60))
    remaining = int(headers.get("x-ratelimit-remaining", 1))
    reset_time = int(headers.get("x-ratelimit-reset", time.time() + 60))
    return limit, remaining, reset_time


def fetch_events(
    max_retries: int = 5, initial_backoff: int = 2, max_backoff: int = 60
) -> Tuple[List[dict[str, Any]], int, int, int]:

    GITHUB_TOKEN = settings.GITHUB_TOKEN
    url = "https://api.github.com/events"
    headers: dict[str, str] = {}
    initial_backoff = 2
    max_backoff = 60
    backoff = initial_backoff
    retries = 0
    needed_type_events = {"PullRequestEvent", "WatchEvent", "IssuesEvent"}

    etag = load_etag()
    if etag:
        headers["If-None-Match"] = etag

    headers["Authorization"] = f"token {GITHUB_TOKEN}"

    while retries < max_retries:

        try:
            response = httpx.get(url, headers=headers)
        except httpx.RequestError as exc:
            print(f"Connection error: {exc}. Retrying in {backoff} seconds.")
            time.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
            retries += 1
            continue

        if response.status_code == 304:
            print("No new events. (HTTP 304)")
            limit, remaining, reset_time = parse_rate_limit_headers(response.headers)
            return [], limit, remaining, reset_time

        elif response.status_code == 200:

            new_etag = response.headers.get("etag")
            if new_etag:
                save_etag(new_etag)
            filtered_events = [
                {
                    "id": e["id"],
                    "type": e["type"],
                    "repo": e.get("repo", {}).get("name", None),
                    "created_at": e["created_at"],
                }
                for e in response.json()
                if e["type"] in needed_type_events
            ]

            limit, remaining, reset_time = parse_rate_limit_headers(response.headers)

            return filtered_events, limit, remaining, reset_time

        elif response.status_code in (401, 403, 429):
            reset_time = int(
                response.headers.get("x-ratelimit-reset", time.time() + 60)
            )
            wait = max(reset_time - time.time(), 1)
            print(
                f"Rate limited or auth error: {response.status_code}. Waiting {wait:.0f} seconds."
            )
            limit, remaining, reset_time = parse_rate_limit_headers(response.headers)
            time.sleep(wait)
            return [], limit, remaining, reset_time

        elif 500 <= response.status_code < 600:
            print(
                f"Server error {response.status_code}. Retrying in {backoff} seconds."
            )
            time.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
            retries += 1
            continue

        else:
            print(f"Unexpected error: {response.status_code} - {response.text}")
            limit, remaining, reset_time = parse_rate_limit_headers(response.headers)
            time.sleep(10)
            return [], limit, remaining, reset_time

    print("Max retries reached, giving up for this cycle.")
    return [], 0, 0, int(time.time() + 60)
