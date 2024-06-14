# from MyAnalysis import MyAnalysis
# from MyOutput import WordPrinter
# from MyInput import MyInput
# from MyStockResearch import MyStockResearch
# from MyInputManager import MyInputManager
# from Index_Stocks import Index_Stocks
import sys
from colorama import Fore, Style
import yfinance as yf
import requests_cache
from requests import Session
from requests_cache import CacheMixin, SQLiteCache
from requests_ratelimiter import LimiterMixin, MemoryQueueBucket
from pyrate_limiter import Duration, RequestRate, Limiter
from StockApp.stock_analysis.StockAnalysis import Analysis
from StockApp.InputManager import StockInput, StockInputManager 

class CachedLimiterSession(CacheMixin, LimiterMixin, Session):
    pass

session = CachedLimiterSession(
    limiter=Limiter(RequestRate(2, Duration.SECOND*5)),  # max 2 requests per 5 seconds
    bucket_class=MemoryQueueBucket,
    backend=SQLiteCache("yfinance.cache"),
    )

def main():

    # Run Input Parser and Check for Input Errors
    input_manager = StockInputManager()
    if(input_manager.conduct_stockapp_input_checks()):
        args = input_manager.grab_args()
    else:
        sys.exit(0)

    if args is None:
        print(args.h)
        sys.exit(0)
    # Open Word Doc file for Output
    output = None
    if args.output is not None or args.report:
        if not args.debug:
            output = WordPrinter(args.output, args.debug)
    else:
        print("StockApp --> Output File will NOT be created all outputs will be to terminal.")

    # Check if there is an input file to read for tickers
    if args.input is not None or args.report:
        if(args.debug):
            print("StockApp -- > Reading Input File: ", args.input)
        inputfile = StockInput(args.input, args.debug)
        ticker_list = inputfile.read_txt_file()
        if(args.debug):
            print("StockApp --> Analysing the following Tickers: ", ticker_list)

        #Form the stocks only once from the List
        listed_stocks = [yf.Ticker(symbol) for symbol in ticker_list]

        analysis = Analysis(listed_stocks, args.time_delta, args.debug)
        analysis.execute_stock_program(args, output)

    # Conduct analysis with only one stock
    if args.ticker is not None:
        stock = [yf.Ticker(args.ticker)]
        analysis = Analysis(stock, args.time_delta, args.debug)
        analysis.execute_stock_program(args, output)

    # Okay now check if we are conducting a monthly report
    if args.report:
        report_analysis = Analysis(stock_list=listed_stocks, time_delta=args.time_delta, debug=args.debug)
        report_analysis.conduct_monthly_report(args, output)

    # Okay now check if we are conducting Research outside of monthly report
    if args.suggest:
        research = StockResearch()
        research.get_ticker_symbols()
        all_tickers = research.list_ticker_symbols()
        chosen_tickers = research.choose_tickers(all_tickers, int(args.number_to_research))
        chosen_stocks = yf.Tickers(chosen_tickers)

        research_analysis = Analysis(chosen_stocks, args.time_delta, args.debug)
        research_analysis.execute_stock_program(args, output)

    # Save file
    if args.output is not None or args.report:
        if not args.debug:
            output.save()

if __name__ == "__main__":
    main()
