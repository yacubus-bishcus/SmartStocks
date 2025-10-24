# Imported Modules 
import sys
from requests import Session
from requests_cache import CacheMixin, SQLiteCache
from requests_ratelimiter import LimiterMixin, MemoryQueueBucket
from pyrate_limiter import Duration, RequestRate, Limiter
import time
import logging
import matplotlib.pyplot as plt 

# My Modules 
from OutputManager import SmartStocksOutput
from SmartStocksInputManager import SmartStocksInputManager
from ArgsParser import ArgsParser
from SmartStocksResearch import Research 
from SmartStocksClock import SmartStocksClock

class CachedLimiterSession(CacheMixin, LimiterMixin, Session):
    pass

session = CachedLimiterSession(
    limiter=Limiter(RequestRate(2, Duration.SECOND*5)),  # max 2 requests per 5 seconds
    bucket_class=MemoryQueueBucket,
    backend=SQLiteCache("yfinance.cache"),
    )


logging.basicConfig(level=logging.INFO)  # Set the logging level to INFO or DEBUG as needed
logger = logging.getLogger(__name__)    # Create a logger for your module

def run():

    # Run Input Parser and Check for Input Errors
    input_manager = SmartStocksInputManager()
    parser = ArgsParser()
    args = parser.terminal_parse_args()
    if args is None:
        logger.warning("INPUT ERROR. Attempting to print Arguments to log.")
        logger.warning(f"Argument: {args}")
        return f"INPUT ERROR. Argument: {args}"
    
    logger.debug(f"Argument: {args}")
    if not parser.conduct_smartstock_input_checks():
        return 

    if args is None:
        print(args.h)
        sys.exit(1)

    # Open Word Doc file for Output
    output = None
    if args.output is not None:
        output = SmartStocksOutput(args.output, "output", args)
        output.smartstock_heading()
    else:
        logger.warning("--> Output File will NOT be created all outputs will be to terminal.")
    
    research = None 
    if args.research:
        research = Research(args.data, args.number_to_research)

    input_manager.tickers = (args.ticker, args.input, args.u, research)
    input_manager.stocks = (input_manager.tickers)

    # Determine ETC 
    SmartStocksClock.guess_etc(args.processes, len(input_manager.stocks), args.number_to_highlight, args.simulations, args.sim_time, args.model_interval, args.report)

    if len(input_manager.tickers) > 0: 
        result = input_manager.apply_input_conditions(output=output, args=args)
        if args.simulations > 0 and not args.report and args.show_plot:
            plt.show()
        elif args.simulations > 0 and not args.report and output is not None:
            output.savefig(result)
    else:
        logger.error("No Tickers Found. Program Exiting.")

if __name__ == "__main__":
    start_time = time.time()
    logger.info("Starting StockApp Program...")
    run()
    end_time = time.time()
    elapsed_time = end_time - start_time
    # Print the elapsed time
    logger.info("Program completed successfully.")
    logger.info(f"Program took {elapsed_time:.2f} seconds to run.")