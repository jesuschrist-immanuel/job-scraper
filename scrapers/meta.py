from selenium import webdriver # type: ignore
from selenium.webdriver.chrome.service import Service # type: ignore
from selenium.webdriver.chrome.options import Options # type: ignore
from selenium.webdriver.common.by import By # type: ignore
from selenium.webdriver.support.ui import WebDriverWait # type: ignore
from selenium.webdriver.support import expected_conditions as EC # type: ignore
from database.db import SessionLocal
from database.models import JobListing
import logging
import time

def scrape_meta_jobs():
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Set up Chrome options for headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    # Initialize the Chrome driver with the options
    driver = webdriver.Chrome(options=chrome_options)

    # Create a new session
    session = SessionLocal()

    try:
        # Fetch all current job IDs from the database
        current_job_ids = {job.job_id for job in session.query(JobListing.job_id).filter_by(company="Meta").all()}

        base_url = 'https://www.metacareers.com/jobs/?teams[0]=Internship%20-%20Engineering%2C%20Tech%20%26%20Design&teams[1]=Internship%20-%20Business&teams[2]=Internship%20-%20PhD'
        driver.get(base_url)
        wait = WebDriverWait(driver, 20)
        links = []
        new_job_ids = set()

        try:
            # Find all the job cards
            job_cards = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[role="link"]')))
            for i in range(len(job_cards)):
                # Re-find the job cards to avoid stale element reference
                job_cards = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[role="link"]')))
                job_card = job_cards[i]

                # Click the job card to open the link in a new tab
                job_card.click()
                time.sleep(2)  # Wait for the new tab to open

                # Switch to the new tab
                driver.switch_to.window(driver.window_handles[-1])

                # Get the URL of the new tab
                job_link = driver.current_url
                links.append(job_link)

                # Close the new tab
                driver.close()

                # Switch back to the original tab
                driver.switch_to.window(driver.window_handles[0])
        except Exception as links_e:
            logger.error(f"An error occurred: {links_e}")

        for link in links:
            driver.get(link)
            
            job_id = link.rstrip('/').split('/')[-1]
            new_job_ids.add(job_id)
            
            try:
                title = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="careersContentContainer"]/div/div[2]/div/div/div[2]/div/div[2]/div[1]'))).text
                
                description = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="careersContentContainer"]/div/div[3]/div[2]/div/div/div[1]/div[1]/div[1]'))).text
                
                loc_div = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="careersContentContainer"]/div/div[2]/div/div/div[2]/div/div[3]/div/div/div[2]')))
                if "more" in loc_div.text:
                    more_spn = wait.until(EC.presence_of_element_located((By.ID, 'showLocationsButton')))
                    more_spn.click()
                loc_as = loc_div.find_elements(By.CSS_SELECTOR, 'a._8lfp._9a80')
                locations = [l.text for l in loc_as]
                
                min_qual_lst = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="careersContentContainer"]/div/div[3]/div[2]/div/div/div[1]/div[1]/div[4]/div[2]/div/ul')))
                min_qual_items = min_qual_lst.find_elements(By.TAG_NAME, 'li')
                min_quals = [q.text for q in min_qual_items]
                pref_qual_lst = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="careersContentContainer"]/div/div[3]/div[2]/div/div/div[1]/div[1]/div[5]/div[2]/div/ul')))
                pref_qual_items = pref_qual_lst.find_elements(By.TAG_NAME, 'li')
                pref_quals = [q.text for q in pref_qual_items]
                qualifications = min_quals + pref_quals
                
                resp_lst = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="careersContentContainer"]/div/div[3]/div[2]/div/div/div[1]/div[1]/div[3]/div[2]/div/ul')))
                resp_items = resp_lst.find_elements(By.TAG_NAME, 'li')
                responsibilities = [r.text for r in resp_items]
                
                misc = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '._1n-_._6hy-._94t2')))[-1].text
                miscellaneous = misc.splitlines()[0]

                # Check if the job listing already exists
                existing_listing = session.query(JobListing).filter_by(job_id=job_id, company="Meta").first()

                if existing_listing:
                    # Update the existing job listing
                    existing_listing.job_link = link
                    existing_listing.title = title
                    existing_listing.company = "Meta"
                    existing_listing.category = None
                    existing_listing.description = description
                    existing_listing.qualifications = qualifications
                    existing_listing.locations = locations
                    existing_listing.miscellaneous = miscellaneous
                    existing_listing.responsibilities = responsibilities
                    logger.info(f"Updated job listing: {job_id}")
                else:
                    # Insert a new job listing
                    job_listing = JobListing(
                        job_link=link,
                        job_id=job_id,
                        title=title,
                        company="Meta",
                        category=None,
                        description=description,
                        qualifications=qualifications,
                        locations=locations,
                        miscellaneous=miscellaneous,
                        responsibilities=responsibilities
                    )
                    session.add(job_listing)
                    logger.info(f"Added new job listing: {job_id}")

                session.commit()
            except Exception as e:
                logger.error(f"An error occurred: {e}")

        # Find job IDs that are no longer present on the website and delete them
        job_ids_to_delete = current_job_ids - new_job_ids
        for job_id in job_ids_to_delete:
            job_to_delete = session.query(JobListing).filter_by(job_id=job_id, company="Meta").first()
            if job_to_delete:
                session.delete(job_to_delete)
                session.commit()
                logger.info(f"Deleted job listing: {job_id}")
    finally:
        driver.quit()
        session.close()
