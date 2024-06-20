# import sys
# import requests_cache
# from requests import Session
# from requests_cache import CacheMixin, SQLiteCache
# from requests_ratelimiter import LimiterMixin, MemoryQueueBucket
# from pyrate_limiter import Duration, RequestRate, Limiter
# from StockApp.OutputManager import WordPrinter, OutputHandler
# from StockApp.InputManager import StockInputManager
# import time
# import logging
#
#
# class CachedLimiterSession(CacheMixin, LimiterMixin, Session):
#     pass
#
# session = CachedLimiterSession(
#     limiter=Limiter(RequestRate(2, Duration.SECOND*5)),  # max 2 requests per 5 seconds
#     bucket_class=MemoryQueueBucket,
#     backend=SQLiteCache("yfinance.cache"),
#     )
#
#
#
# logging.basicConfig(level=logging.INFO)  # Set the logging level to INFO or DEBUG as needed
# logger = logging.getLogger(__name__)    # Create a logger for your module
#
# def main():
#
#     # Run Input Parser and Check for Input Errors
#     input_manager = StockInputManager()
#     if(input_manager.conduct_stockapp_input_checks()):
#         args = input_manager.grab_args()
#     else:
#         sys.exit(1)
#
#     if args is None:
#         print(args.h)
#         sys.exit(1)
#     # Open Word Doc file for Output
#     output = None
#     if args.output is not None:
#         output = WordPrinter(args.output)
#         output.create_document_heading()
#     else:
#         logger.warning("StockApp --> Output File will NOT be created all outputs will be to terminal.")
#
#     input_manager.apply_input_conditions(output=output)
#
#
# if __name__ == "__main__":
#     start_time = time.time()
#     logger.info("Starting StockApp Program...")
#     main()
#     end_time = time.time()
#     elapsed_time = end_time - start_time
#     # Print the elapsed time
#     logger.info("Program completed successfully.")
#     logger.info(f"Program took {elapsed_time:.2f} seconds to run.")
from .SmartStocksApp import SmartStocksApp

if __name__ =="__main__":
    SmartStocksApp().run()
