import logging
import threading
from colorama import Fore, Style
import requests
from bs4 import BeautifulSoup
import ftplib
import os
import pandas as pd 
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import pkg_resources
import time 
import psutil
import sys 

logger = logging.getLogger(__name__)
#############################################################################################################################################
## Research Class 
#############################################################################################################################################
class Research:
    def __init__(self, filenames, number_to_research):
        logger.debug("--> Grabbing All Tickers...")
        self.filenames = filenames
        self._get_ticker_symbols()
        for filename in self.filenames:
            self.clean_data(filename, filename)
            logger.info(f"{filename} data cleaned.")

        all_tickers = self.list_ticker_symbols()
        self._tickers = self.choose_tickers(all_tickers, number_to_research)

    @property 
    def tickers(self):
        return self._tickers 

    def fetch_csv_data(self, url):
        response = requests.get(url)
        response.raise_for_status()
        return response.text

    def _get_ticker_symbols(self):
        # Check if we already have the files
        count = 0

        # Check if we already have the files in the data folder
        for filename in self.filenames:
            filepath = pkg_resources.resource_filename('data', filename)
            if os.path.exists(filepath):
                logger.debug(Fore.GREEN + f"get_ticker_symbols File '{filename}' found in data folder." + Style.RESET_ALL)
                count += 1

        # If all files are found in the data folder, skip download
        if count == len(self.filenames):
            logger.debug(Fore.GREEN + "get_ticker_symbols Skipping download as all files are already present." + Style.RESET_ALL)
        else:
            # Connect to FTP server and download missing files
            ftp_server = ftplib.FTP("ftp.nasdaqtrader.com")
            ftp_server.login()
            ftp_server.cwd('Symboldirectory')

            for filename in self.filenames:
                local_filepath = pkg_resources.resource_filename('data', filename)
                if not os.path.exists(local_filepath):
                    with open(local_filepath, "wb") as file:
                        ftp_server.retrbinary(f"RETR {filename}", file.write)
                    logger.debug(Fore.GREEN + f"get_ticker_symbols Downloaded '{filename}' from FTP server." + Style.RESET_ALL)
                else:
                    logger.debug(Fore.GREEN + f"get_ticker_symbols File '{filename}' already exists locally." + Style.RESET_ALL)

            ftp_server.quit()

    def list_ticker_symbols(self):
        filepath = pkg_resources.resource_filename('data', "nasdaqlisted.txt")
        df = pd.read_csv(filepath, sep="|")
        filepath = pkg_resources.resource_filename('data', "otherlisted.txt")
        df2 = pd.read_csv(filepath, sep="|")
        # filter out ETFs
        filtered_df1 = df[df['ETF'] != "Y"]
        filtered_df2 = df2[df2['ETF'] != "Y"]
        # Combine into one dataframe
        combined_df = pd.concat([filtered_df1, filtered_df2], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=['Symbol'])
        tickers = combined_df['Symbol'].to_list()
        filtered_tickers = [value for value in tickers if isinstance(value, str) and not value.startswith("File")]
        return filtered_tickers

    def compare_files(self, file1, file2):
        with open(file1, 'r') as f1, open(file2, 'r') as f2:
            lines1 = f1.readlines()
            lines2 = f2.readlines()

        # Find lines that are in file1 but not in file2
        lines_unique_to_file1 = [line.strip() for line in lines1 if line.strip() not in lines2]

        # Find lines that are in file2 but not in file1
        lines_unique_to_file2 = [line.strip() for line in lines2 if line.strip() not in lines1]

        return lines_unique_to_file1, lines_unique_to_file2

    def choose_tickers(self, my_list, number):
        random_tickers = random.sample(my_list, number)
        logger.debug("choose_tickers Tickers Chosen --> ", random_tickers)
        return random_tickers

    def read_data(self, input_filename):
        input_filename = pkg_resources.resource_filename('data', input_filename)
        try:
            df = pd.read_csv(input_filename, delimiter='|')
        except FileNotFoundError:
            logger.error(f"read_txt_file --> Error: File '{input_filename}' not found.")
            exit(1)
        except pd.errors.EmptyDataError:
            logger.error(f"read_txt_file --> Error: File '{input_filename}' is empty or cannot be read as CSV.")
            exit(1)

        return df

    def clean_data(self, input_filename=None, output_filename=None):
        # Read data into a DataFrame
        df = self.read_data(input_filename)
        before = len(df)
        if input_filename == "nasdaqlisted.txt":
            filtered_df = df[(df['ETF'] != 'Y') &
                     (df['Financial Status'] == 'N') &
                     (df['Test Issue'] != 'Y') &
                     (df['NextShares'] != 'Y') &
                     (df['Market Category'] != 'N')]
        elif input_filename == "otherlisted.txt":
            filtered_df = df[(df['ETF'] != 'Y') & (df['Test Issue'] != 'Y')]

        # Remove rows with "Warrant" in the 'Security Name' column
        filtered_df = filtered_df[~filtered_df['Security Name'].str.contains("Warrant", case=False, na=False)]
        # remove rows with "rights" in the security name column 
        filtered_df = filtered_df[~filtered_df['Security Name'].str.contains("Rights", case=False, na=False)]
        df_cleaned = filtered_df.dropna(subset=['ETF'])
        after = len(df_cleaned)
        # Write filtered data to a new file
        try:
            output_filename = pkg_resources.resource_filename('data', output_filename)
            df_cleaned.to_csv(output_filename, sep='|', index=False)  # Writing as tab-delimited data
            logger.info(f"clean_data --> Filtered data has been written to '{output_filename}'.")
            logger.info(f"clean_data Total filtered Rows --> {before-after}")
        except PermissionError:
            logger.exception(f"InputManager::clean_data --> Error: Permission denied to write to '{output_filename}'.")
            exit(1)
        except Exception as e:
            logger.exception(f"InputManager::clean_data --> Error occurred while writing to '{output_filename}': {str(e)}")
            exit(1)

        return df_cleaned

    def remove_stock(self, ticker):
        # figure out which file it came from
        filtered_df = pd.DataFrame()
        for filename in self.filenames:
            df = self.read_data(filename)
            before = len(df)
            if filename == "nasdaqlisted.txt":
                filtered_df = df[(df['Symbol'] != ticker)]
            elif filename == "otherlisted.txt":
                filtered_df = df[(df['NASDAQ Symbol'] != ticker)]
            else:
                try:
                    filtered_df = df[(df['Symbol'] != ticker)]
                except:
                    logger.exception("Couldn't apply remove stock function to your list because no 'Symbol' list key found.")

            after = len(filtered_df)
            output_filename = filename
            try:
                output_filename = pkg_resources.resource_filename('data', output_filename)
                filtered_df.to_csv(output_filename, sep='|', index=False)  # Writing as tab-delimited data
                logger.info(f"clean_data --> Filtered data has been written to '{output_filename}'.")
                logger.info(f"clean_data Total filtered Rows --> {before-after}")
            except PermissionError:
                logger.exception(f"InputManager::clean_data --> Error: Permission denied to write to '{output_filename}'.")
                exit(1)
            except Exception as e:
                logger.exception(f"InputManager::clean_data --> Error occurred while writing to '{output_filename}': {str(e)}")
                exit(1)

#############################################################################################################################################
## InternetResearch Class 
#############################################################################################################################################
class InternetResearch:
    def __init__(self):
        self.driver = None
        self.thread = None
        self._stop_event = threading.Event()

    def get_top_gainers(self, url="https://finance.yahoo.com/gainers", callback=None):
        logger.info("Grabbing top Gainers...")
        start_time = time.time()

        # Setup Chrome options
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        #options.add_extension('/path/to/ublock.crx')  # Path to your adblock extension
        # Add capabilities to options
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        # Initialize WebDriver
        self.driver = webdriver.Chrome(service=Service(), options=options)

        try:
            # Enable Network Interception
            self.driver.execute_cdp_cmd('Network.enable', {})
            self.driver.execute_cdp_cmd('Network.setBlockedURLs', {"urls": ["*.jpg", "*.png", "*.gif", "*.css", "*.js", "*.ads"]})
            # Open URL
            self.driver.get(url)
            logger.info("Driver Got URL")

            # Parse the HTML content using BeautifulSoup
            if not self._stop_event.is_set():
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                table = soup.find('table', {'class': 'W(100%)'})

                if table:
                    rows = table.find('tbody').find_all('tr')[:3]
                    logger.info("Making Top Stocks Table...")

                    top_stocks = []
                    for row in rows:
                        cols = row.find_all('td')
                        stock = {
                            'symbol': cols[0].text.strip(),
                            'name': cols[1].text.strip(),
                            'price': cols[2].text.strip(),
                            'change': cols[3].text.strip(),
                            'percent_change': cols[4].text.strip(),
                            'volume': cols[5].text.strip()
                        }
                        top_stocks.append(stock)

                    logger.info("Top Stocks Table Made...")
                    end_time = time.time()
                    elapsed_time = end_time - start_time
                    logger.info(f"Grabbing Top Stocks took {elapsed_time:.2f} seconds to run.")
                    if callback:
                        callback(top_stocks)
                    return top_stocks
                else:
                    logger.warning("Table returned nonetype")
            else:
                logger.info("WebDriverWait interrupted by stop event.")
        except Exception as e:
            logger.error(f"An error occurred: {e}")
        finally:
            self.quit_driver(force=False)

        return []

    def quit_driver(self, force=False):
        time2_start = time.time()
        try:
            if self.driver:
                self.driver.quit()
        except Exception as e:
            logger.error(f"Error quitting driver: {e}")
        finally:
            if force:
                self.force_quit_driver()
            self.driver = None
            time2_end = time.time()
            time_elapsed2 = time2_end - time2_start 
            logger.info(f"Quiting driver took {time_elapsed2:.2f} seconds to run.")

    def force_quit_driver(self):
        if self.driver:
            try:
                process = psutil.Process(self.driver.service.process.pid)
                for proc in process.children(recursive=True):
                    proc.kill()
                process.kill()
                logger.info("Forcefully terminated the WebDriver process.")
            except Exception as e:
                logger.error(f"Error forcefully terminating the WebDriver process: {e}")

    def start_get_top_gainers_thread(self, callback=None, url="https://finance.yahoo.com/gainers"):
        self._stop_event.clear()
        self.thread = threading.Thread(target=self.get_top_gainers, args=(url, callback))
        self.thread.start()

    def stop_thread(self):
        if self.thread and self.thread.is_alive():
            self._stop_event.set()
            self.quit_driver(force=True)
            self.thread.join()

    def signal_handler(self, sig, frame):
        logger.info("Exiting application...")
        self.stop_thread()
        sys.exit(0)

#############################################################################################################################################
## HandleSoup Class 
#############################################################################################################################################
class HandleSoup:
    @staticmethod
    def find_and_print_soup_content(soup, target_word, content_amount=1000):
        # Find all text elements in the soup
        text_elements = soup.find_all(text=True)

        # Join all text elements into a single string
        full_text = ' '.join(text_elements)

        # Find the index of the target word in the full text
        word_index = full_text.find(target_word)

        if word_index != -1:
            # Extract 100 words before and after the target word
            context_start = max(0, word_index - content_amount)
            context_end = min(len(full_text), word_index + len(target_word) + content_amount)
            context = full_text[context_start:context_end]
            # Print the context
            print("Context around '{}':".format(target_word))
            print(context)
        else:
            print("Word '{}' not found in the text.".format(target_word))

    @staticmethod
    def find_elements_by_keyword(soup, keyword):
        # Find all elements containing the keyword in their text or attributes
        elements = soup.find_all(lambda tag: keyword in tag.text or keyword in tag.get('class', []))
        return elements
    

    # @staticmethod
    # def signal_handler(sig, frame): # included 
    #     logger.info("Exiting application...")
    #     research.stop_thread()
    #     sys.exit(0)