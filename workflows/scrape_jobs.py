from scrapers import scrape_apple_jobs, scrape_microsoft_jobs, scrape_google_jobs, scrape_amazon_jobs, scrape_meta_jobs, scrape_tesla_jobs

def main():
    try:
        scrape_apple_jobs()
        scrape_microsoft_jobs()
        scrape_google_jobs()
        scrape_amazon_jobs()
        scrape_meta_jobs()
        scrape_tesla_jobs()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    main()
