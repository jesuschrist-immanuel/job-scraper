# TODO: build nvidia, amazon, meta, and tesla scrapers

from scrapers.apple import scrape_apple_jobs
from scrapers.microsoft import scrape_microsoft_jobs
from scrapers.nvidia import scrape_nvidia_jobs
from scrapers.google import scrape_google_jobs

__all__ = [
    "scrape_apple_jobs",
    "scrape_microsoft_jobs",
    "scrape_nvidia_jobs",
    "scrape_google_jobs"
]
