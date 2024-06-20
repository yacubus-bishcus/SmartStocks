## -----------------------------------------------------------------------------------------##
## ----------------------------- Research CLASS    ----------- -----------------------------##
## -----------------------------------------------------------------------------------------##
from .StockAnalysis import Analysis
import logging
from colorama import Fore, Style
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import ftplib
import os
import random
from selenium import webdriver
import pkg_resources

logger = logging.getLogger(__name__)

class Research:
    def __init__(self, args=None):
        self.args = args
        logger.debug("--> Grabbing All Tickers...")
        self.filenames = self.args.data
        self._get_ticker_symbols()
        for filename in self.filenames:
            self.clean_data(filename, filename)
            logger.info(f"{filename} data cleaned.")

        all_tickers = self.list_ticker_symbols()
        self.chosen_tickers = self.choose_tickers(all_tickers, int(self.args.number_to_research))


    def fetch_csv_data(self, url):
        response = requests.get(url)
        response.raise_for_status()
        return response.text

    def _get_ticker_symbols(self):
        # Check if we already have the files
        count = 0

        # Check if we already have the files in the data folder
        for filename in self.filenames:
            filepath = pkg_resources.resource_filename('StockApp.data', filename)
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
                local_filepath = pkg_resources.resource_filename('StockApp.data', filename)
                if not os.path.exists(local_filepath):
                    with open(local_filepath, "wb") as file:
                        ftp_server.retrbinary(f"RETR {filename}", file.write)
                    logger.debug(Fore.GREEN + f"get_ticker_symbols Downloaded '{filename}' from FTP server." + Style.RESET_ALL)
                else:
                    logger.debug(Fore.GREEN + f"get_ticker_symbols File '{filename}' already exists locally." + Style.RESET_ALL)

            ftp_server.quit()

    def grab_research_tickers(self):
        return self.chosen_tickers

    def list_ticker_symbols(self):
        filepath = pkg_resources.resource_filename('StockApp.data', "nasdaqlisted.txt")
        df = pd.read_csv(filepath, sep="|")
        filepath = pkg_resources.resource_filename('StockApp.data', "otherlisted.txt")
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

    def grab_dogs_of_the_dow(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(options=options)

        # Send a GET request to the Dogs of the Dow website
        url = 'https://www.dogsofthedow.com/dogday.htm'
        driver.get(url)
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        # Find the table containing the tickers
        table = soup.find('table', class_='tablepress tablepress-id-5 tablepress-responsive dataTable no-footer')
        # Extract tickers from the table
        tickers = []
        if table:
            for row in table.find_all('tr')[1:]:  # Skip header row
                ticker = row.find_all('td')[0].text.strip()
                tickers.append(ticker)

        else:
            logger.error(Fore.RED + "grab_dogs_of_the_dow " \
            "--> Failed to find Table of tickers." + Style.RESET_ALL)

        driver.quit()
        return soup

    def find_and_print_soup_content(self, soup, target_word, content_amount=1000):
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

    def find_elements_by_keyword(self, soup, keyword):
        # Find all elements containing the keyword in their text or attributes
        elements = soup.find_all(lambda tag: keyword in tag.text or keyword in tag.get('class', []))
        return elements

    # Example usage:
    # Assuming 'soup' is the BeautifulSoup object and 'keyword' is the keyword to search for
    # Replace 'soup' and 'keyword' with your specific values

    # Find elements containing the keyword
    #found_elements = find_elements_by_keyword(soup, 'Symbol')

    def read_data(self, input_filename):
        input_filename = pkg_resources.resource_filename('StockApp.data', input_filename)
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

        df_cleaned = filtered_df.dropna(subset=['ETF'])
        after = len(df_cleaned)
        # Write filtered data to a new file
        try:
            output_filename = pkg_resources.resource_filename('StockApp.data', output_filename)
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
                output_filename = pkg_resources.resource_filename('StockApp.data', output_filename)
                filtered_df.to_csv(output_filename, sep='|', index=False)  # Writing as tab-delimited data
                logger.info(f"clean_data --> Filtered data has been written to '{output_filename}'.")
                logger.info(f"clean_data Total filtered Rows --> {before-after}")
            except PermissionError:
                logger.exception(f"InputManager::clean_data --> Error: Permission denied to write to '{output_filename}'.")
                exit(1)
            except Exception as e:
                logger.exception(f"InputManager::clean_data --> Error occurred while writing to '{output_filename}': {str(e)}")
                exit(1)
