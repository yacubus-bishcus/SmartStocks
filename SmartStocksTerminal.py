# Imported Modules 
import sys
from requests import Session
from requests_cache import CacheMixin, SQLiteCache
from requests_ratelimiter import LimiterMixin, MemoryQueueBucket
from pyrate_limiter import Duration, RequestRate, Limiter
import time
import logging

# My Modules 
from OutputManager import WordPrinter
from InputManager import StockInputManager
from ArgsParser import ArgsParser
from Research import Research 


class CachedLimiterSession(CacheMixin, LimiterMixin, Session):
    pass

session = CachedLimiterSession(
    limiter=Limiter(RequestRate(2, Duration.SECOND*5)),  # max 2 requests per 5 seconds
    bucket_class=MemoryQueueBucket,
    backend=SQLiteCache("yfinance.cache"),
    )


logging.basicConfig(level=logging.INFO)  # Set the logging level to INFO or DEBUG as needed
logger = logging.getLogger(__name__)    # Create a logger for your module

def SmartStocksTerminal():

    # Run Input Parser and Check for Input Errors
    input_manager = StockInputManager()
    parser = ArgsParser()
    args = parser.terminal_parse_args()
    if args is None:
        logger.warning("INPUT ERROR. Attempting to print Arguments to log.")
        logger.warning(f"Argument: {args}")
        return f"INPUT ERROR. Argument: {args}"
    
    logger.debug(f"Argument: {args}")
    parser.conduct_stockapp_input_checks()

    if args is None:
        print(args.h)
        sys.exit(1)
    # Open Word Doc file for Output
    output = None
    if args.output is not None:
        output = WordPrinter(args.output)
        output.create_document_heading()
    else:
        logger.warning("StockApp --> Output File will NOT be created all outputs will be to terminal.")
    
    research = None 
    if args.research:
        research = Research(args.data, args.number_to_research)

    input_manager.tickers = (args.ticker, args.input, args.u, research)
    input_manager.stocks = (input_manager.tickers)
    input_manager.apply_input_conditions(output=output, args=args)


if __name__ == "__main__":
    start_time = time.time()
    logger.info("Starting StockApp Program...")
    SmartStocksTerminal()
    end_time = time.time()
    elapsed_time = end_time - start_time
    # Print the elapsed time
    logger.info("Program completed successfully.")
    logger.info(f"Program took {elapsed_time:.2f} seconds to run.")