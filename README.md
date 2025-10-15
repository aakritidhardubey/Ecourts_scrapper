# eCourts India Scraper

A Python-based web scraper for the eCourts India portal that automates case status searches and downloads daily cause lists from district courts.

## Features

- **Case Status Search**: Search for any case using its CNR (Case Number Reference) number
- **Cause List Download**: Download complete daily cause lists from district courts in JSON format
- **PDF Download**: Download final orders/judgements for disposed cases
- **Interactive Browser Automation**: Handles CAPTCHA manually while automating the rest

## Requirements

- Python 3.7+
- Google Chrome browser
- ChromeDriver (compatible with your Chrome version)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ecourts-scraper.git
   cd ecourts-scraper
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install ChromeDriver**
   - Download from: https://chromedriver.chromium.org/
   - Place in your system PATH or project directory

4. **Create configuration file**
   
   Create a `config.json` file in the project root:
   ```json
   {
     "state_code": "XX",
     "dist_code": "YY",
     "court_code": "ZZ"
   }
   ```
   (These codes are specific to your target court and can be found on the eCourts website)

## Usage

### 1. Download Cause List

Download today's cause list:
```bash
python ecourts_scraper.py download-causelist
```

Download tomorrow's cause list:
```bash
python ecourts_scraper.py download-causelist --tomorrow
```

**Process:**
1. Browser opens automatically to the eCourts cause list page
2. Select your State, District, Court Complex, and Establishment
3. Select the date from calendar
4. Solve the CAPTCHA
5. Click 'Civil' or 'Criminal' button
6. Script automatically extracts and saves the data as JSON and pdf file

**Output:** Saved in `cause_lists/` folder as `causelist_DD_MM_YYYY_HHMMSS.json` and pdf as `causelist_DD_MM_YYYY_HHMMSS.json`

### 2. Search Case Status

Search by CNR number:
```bash
python ecourts_scraper.py search --cnr XXXXXXXXXXXXXXXXXXXX
```

Download final order PDF (if available):
```bash
python ecourts_scraper.py search --cnr XXXXXXXXXXXXXXXXXXXX --download-pdf
```

**Process:**
1. Browser opens and navigates to CNR search
2. Enters the CNR number
3. You solve the CAPTCHA and click Search
4. Script displays case details and listing status
5. Downloads PDF if requested and available

**Output:** Case details printed to console, PDFs saved in `case_orders/` folder

## Project Structure

```
ecourts-scraper/
│
├── ecourts_scraper.py      # Main script
├── pdf_generator.py        # pdf generation file
├── config.json             # Court configuration
├── requirements.txt        # Python dependencies
├── README.md              # This file
│
├── cause_lists/           # Downloaded cause lists (JSON)
│   └── causelist_DD_MM_YYYY_HHMMSS.json
│
└── case_orders/           # Downloaded court orders (PDF)
    └── order_XXXXXX.pdf
```

## Dependencies

```
requests
beautifulsoup4
selenium
click
lxml
reportlab
```

Install all at once:
```bash
pip install requests beautifulsoup4 selenium click lxml reportlab
```

## How It Works

### Cause List Scraping
1. Opens automated Chrome browser to eCourts portal
2. Waits for user to fill form and solve CAPTCHA
3. Detects results in iframe or main page
4. Extracts table data using BeautifulSoup
5. Saves structured data as JSON with timestamp

### Case Status Search
1. Navigates to CNR search page
2. Inputs CNR number programmatically
3. Waits for user to solve CAPTCHA
4. Parses case details and hearing dates
5. Optionally downloads final orders


## Troubleshooting

**"Selenium not installed"**
```bash
pip install selenium
```

**"ChromeDriver not found"**
- Ensure ChromeDriver is installed and in PATH
- Or place chromedriver.exe in project folder

**"Timed out waiting for results"**
- You may have taken too long to fill the form (5 min limit)
- No cause list may be available for that date
- Check if you selected the correct date

**"Could not find hearings table"**
- Ensure you clicked 'Civil' or 'Criminal' button after solving CAPTCHA
- Wait for the results to fully load before timeout

## Notes

- The script requires manual CAPTCHA solving (by design, for ethical scraping)
- Each cause list is saved with a timestamp to prevent overwriting
- Browser stays open after scraping for verification
- All data is saved locally in structured JSON format

## Future Enhancements

- Batch processing for multiple dates
- Excel export functionality
- Automated scheduling for daily downloads
- Email notifications for case listings

## Demo Video

[Insert YouTube/Drive link to demo video]

---

**Note**: This tool is for educational and research purposes. Please respect eCourts India's terms of service and use responsibly.