import requests
import os
import json
import re
import time
from bs4 import BeautifulSoup
from datetime import date, timedelta, datetime
import click

# --- Selenium Imports ---
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    SELENIUM_SUPPORT = True
except ImportError:
    SELENIUM_SUPPORT = False

from pdf_generator import convert_causelist_to_pdf

# --- Configuration ---
BASE_URL = "https://services.ecourts.gov.in/ecourtindia_v6/"

def load_config():
    """Load court codes from config.json"""
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: config.json not found.")
        print("Please create it with your state_code, dist_code, and court_code.")
        return None

# --- Cause List Scraper (Interactive via Selenium) ---

def download_causelist_with_selenium(config, for_date):
    """
    Opens a browser, lets the user solve the CAPTCHA, handles the iframe,
    waits for the hearings table to load, and scrapes the data into a JSON file.
    """
    print(f"\n{'='*60}")
    print(f"📋 Starting interactive download for cause list of {for_date}")
    print(f"{'='*60}\n")

    driver = None
    try:
        driver = webdriver.Chrome()
        driver.get(BASE_URL + "?p=cause_list/index")

        print("\n" + "!"*60)
        print("ACTION REQUIRED: The browser has opened.")
        print("1. Please select your State, District, Court Complex, and Establishment.")
        print("2. Select the correct Date from the calendar.")
        print("3. Solve the CAPTCHA.")
        print("4. Click the 'Civil' or 'Criminal' button to view the list.")
        print("!"*60 + "\n")

        cases = []
        # Check if results are in an iframe
        try:
            WebDriverWait(driver, 30).until(
                EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe"))
            )
            print("✓ Switched to results iframe.")
            
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.XPATH, "//table"))
            )
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'lxml')
            hearings_table = soup.find('table')
                
        except TimeoutException:
            # Check main page if no iframe
            driver.switch_to.default_content()
            
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.XPATH, "//table"))
            )
            
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'lxml')
            
            # Find the largest table 
            all_tables = soup.find_all('table')
            hearings_table = max(all_tables, key=lambda t: len(t.find_all('tr'))) if all_tables else None

        if not hearings_table:
            print(" Could not find the hearings table.")
            return driver

        # Extract headers and data
        headers = [th.text.strip() for th in hearings_table.find_all('th')]
        
        if not headers:
            first_row = hearings_table.find('tr')
            if first_row:
                headers = [td.text.strip() for td in first_row.find_all('td')]
        
        rows = hearings_table.find_all('tr')[1:] if headers else hearings_table.find_all('tr')
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) > 0:
                if headers:
                    case_data = {headers[i]: cell.text.strip() for i, cell in enumerate(cells) if i < len(headers)}
                else:
                    case_data = {f"Column_{i+1}": cell.text.strip() for i, cell in enumerate(cells)}
                cases.append(case_data)

        print(f"✓ Scraped {len(cases)} cases from the cause list.")

        if cases:
            os.makedirs("cause_lists", exist_ok=True)
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"causelist_{for_date.replace('-', '_')}_{timestamp}.json"
            save_path = os.path.join("cause_lists", filename)
            
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(cases, f, indent=2, ensure_ascii=False)
            print(f"Success! Scraped data saved to: {save_path}")
        else:
            print(" No cases found.")

        driver.switch_to.default_content()
        return driver,save_path

    except TimeoutException:
        print("\n Timed out waiting for the results to load.")
        if driver: driver.quit()
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        if driver: driver.quit()
        return None
    

# --- Case Status Search (By CNR Number) ---

def search_case_status(cnr):
    """Automates browser to fetch case status using CNR number."""
    if not SELENIUM_SUPPORT:
        return None, None

    print("\n" + "=" * 60)
    print("Starting browser automation...")
    print("=" * 60)

    driver = None
    try:
        driver = webdriver.Chrome()
        driver.get(BASE_URL)

        print("Navigating to CNR Search page...")
        WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.ID, "cino"))).click()

        print("Entering CNR Number...")
        cnr_input_field = WebDriverWait(driver, 50).until(EC.presence_of_element_located((By.ID, "cino")))
        cnr_input_field.send_keys(cnr)

        print("\n" + "!" * 60)
        print("ACTION REQUIRED: Please solve CAPTCHA and click 'Search'.")
        print("The script will wait for the results to load.")
        print("!" * 60 + "\n")

        WebDriverWait(driver, 300).until(
            EC.presence_of_element_located((By.XPATH, "//div[@id='history_cnr']//table[contains(@class, 'case_status_table')]"))
        )
        print("Case details loaded successfully.")
        return driver, driver.page_source

    except TimeoutException:
        print("Timeout: CAPTCHA not solved or invalid CNR.")
        if driver:
            time.sleep(30)
            driver.quit()
        return None, None
    except Exception as e:
        print(f"Error during browser automation: {e}")
        if driver:
            driver.quit()
        return None, None

# --- HTML Parser for Case Details ---

def parse_and_display_results(page_source):
    """Parses the HTML to find and display case status and listing info."""
    print("\n--- Parsing Page for Case Details ---")
    soup = BeautifulSoup(page_source, "lxml")

    # Locate main status table
    status_table = soup.find("table", class_="case_status_table")
    if not status_table:
        print("Critical: Could not find the main 'case_status_table'.")
        return

    all_details = {}
    for row in status_table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) >= 2:
            key = cells[0].text.strip()
            value = cells[1].text.strip()
            all_details[key] = value

    print("\n--- Case Details ---")

    if "Next Hearing Date" in all_details:
        print(f"Status: Pending")
        print(f"Case Stage: {all_details.get('Case Stage', 'N/A')}")
        print(f"Court / Judge: {all_details.get('Court Number and Judge', 'N/A')}")
    elif "Decision Date" in all_details:
        print(f"Status: {all_details.get('Case Status', 'Disposed')}")
        print(f"Decision Date: {all_details.get('Decision Date', 'N/A')}")
    else:
        print("Status: Unknown (Layout may have changed)")

    print("---------------------\n")

    next_hearing_date_str = all_details.get("Next Hearing Date")

    if next_hearing_date_str:
        hearing_date_obj = None
        try:
            cleaned_date_str = next_hearing_date_str.replace('st', '').replace('nd', '').replace('rd', '').replace('th', '')
            hearing_date_obj = datetime.strptime(cleaned_date_str, '%d %B %Y').date()
        except ValueError:
            print(f"Could not parse the date format: {next_hearing_date_str}")

        if hearing_date_obj:
            today = date.today()
            tomorrow = today + timedelta(days=1)

            if hearing_date_obj == today or hearing_date_obj == tomorrow:
                print("CASE IS LISTED!")
                print(f"Listing Date: {next_hearing_date_str}")
                print(f"Purpose: {all_details.get('Case Stage', 'N/A')}")
            elif hearing_date_obj > tomorrow:
                print("The case is not listed for a hearing today or tomorrow.")
                print(f"Next scheduled hearing: {next_hearing_date_str}")
            else:
                print("The case is not listed for a hearing today or tomorrow (past date).")
    else:
        print("No 'Next Hearing Date' found (likely disposed).")

# --- Final Order / Judgement Downloader ---

def download_final_order(driver, page_source):
    """Downloads the final order PDF from the case details page."""
    print("\n" + "=" * 60)
    print("Searching for Final Order PDF...")
    print("=" * 60)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'final orders / judgements')]"))
        )

        order_link_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'final orders / judgements')]/following-sibling::table[contains(@class, 'order_table')]//a"))
        )

        onclick_text = order_link_element.get_attribute("onclick")
        match = re.search(r"filename=([^&']+)", onclick_text)
        if not match:
            print("Could not extract PDF link.")
            return

        pdf_path = match.group(1)
        pdf_url = "https://services.ecourts.gov.in" + pdf_path
        print(f"PDF link found: {pdf_url}")

        session = requests.Session()
        for cookie in driver.get_cookies():
            session.cookies.set(cookie['name'], cookie['value'])
        headers = {'Referer': driver.current_url}
        response = session.get(pdf_url, headers=headers, timeout=30)
        response.raise_for_status()

        os.makedirs("case_orders", exist_ok=True)
        save_path = os.path.join("case_orders", os.path.basename(pdf_path))
        with open(save_path, "wb") as f:
            f.write(response.content)
        print(f"PDF saved to: {save_path}")

    except TimeoutException:
        print("No 'Final Orders / Judgements' section found or it is empty.")
    except requests.exceptions.HTTPError as e:
        print(f"Server error while downloading PDF: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

# --- CLI Commands ---

@click.group()
def cli():
    """eCourts Scraper: Search case status or download cause lists."""
    pass

@cli.command(help="Search for a specific case using its CNR number.")
@click.option("--cnr", required=True, help="CNR number of the case.")
@click.option("--download-pdf", is_flag=True, help="Download final order PDF if available.")
def search(cnr, download_pdf):
    driver, page_source = search_case_status(cnr)
    if page_source:
        parse_and_display_results(page_source)
        if download_pdf:
            download_final_order(driver, page_source)
    if driver:
        print("\nClosing browser...")
        driver.quit()

@cli.command(help="[Req #5] Interactively download the entire cause list for a court.")
@click.option("--today", is_flag=True, default=True, help="Fetch for today (default).")
@click.option("--tomorrow", is_flag=True, help="Fetch for tomorrow.")
def download_causelist(today, tomorrow):
    """The command for downloading the full cause list."""
    config = load_config()
    if not config: return
    
    deadline = date(2025, 10, 20)
    if date.today() > deadline:
        print(f"\nNote: The original assignment deadline of {deadline.strftime('%B %dth')} has passed.")

    if tomorrow: target_date = (date.today() + timedelta(days=1)).strftime("%d-%m-%Y")
    else: target_date = date.today().strftime("%d-%m-%Y")
    
    driver,json_path = download_causelist_with_selenium(config, target_date)

    if json_path:
        convert_causelist_to_pdf(json_path)
    if driver:
        print("\nClosing browser...")
        driver.quit()

# --- Entry Point ---

if __name__ == "__main__":
    if not SELENIUM_SUPPORT:
        print("Selenium not installed. Run: pip install selenium")
    else:
        cli()
