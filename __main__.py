import sys
from colorama import Fore, Style
import yfinance as yf
import requests_cache
from requests import Session
from requests_cache import CacheMixin, SQLiteCache
from requests_ratelimiter import LimiterMixin, MemoryQueueBucket
from pyrate_limiter import Duration, RequestRate, Limiter
from StockApp.OutputManager import WordPrinter, OutputHandler
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

    input_manager.apply_input_conditions()

    # Save file
    if args.output is not None or args.report:
        if not args.debug:
            output.save()

    if args.as_pdf:
        output_handler = OutputHandler(args.output)
        output_handler.convert_word_to_pdf()
        
if __name__ == "__main__":
    main()
