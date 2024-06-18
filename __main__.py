import sys
import requests_cache
from requests import Session
from requests_cache import CacheMixin, SQLiteCache
from requests_ratelimiter import LimiterMixin, MemoryQueueBucket
from pyrate_limiter import Duration, RequestRate, Limiter
from StockApp.OutputManager import WordPrinter, OutputHandler
from StockApp.InputManager import StockInputManager
import time
import logging


class CachedLimiterSession(CacheMixin, LimiterMixin, Session):
    pass

session = CachedLimiterSession(
    limiter=Limiter(RequestRate(2, Duration.SECOND*5)),  # max 2 requests per 5 seconds
    bucket_class=MemoryQueueBucket,
    backend=SQLiteCache("yfinance.cache"),
    )



logging.basicConfig(level=logging.INFO)  # Set the logging level to INFO or DEBUG as needed
logger = logging.getLogger(__name__)    # Create a logger for your module

def main():

    # Run Input Parser and Check for Input Errors
    input_manager = StockInputManager()
    if(input_manager.conduct_stockapp_input_checks()):
        args = input_manager.grab_args()
    else:
        sys.exit(1)

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

    input_manager.apply_input_conditions(output=output)
    # Here we design and write the executive summary
    if args.output is not None:
        total_stocks = str(output.grab_report_card_value('total_stocks'))
        output.write(f"The total number of stocks evaluated for this report was {total_stocks}")
        output.write(f"Ran {args.simulations} trials simulating {args.sim_time} days of future prices for each stock using seed {args.seed} with {args.processes} processors.")
        output.write("Weights Used for Weighted Aggregate Merit: " + str(args.weights))
        output.write("Supervised Aggregate Merit Mean Square Error: " + str(output.grab_report_card_value('mse')))
        output.write("Supervised Aggregate Merit R-Squared: " + str(output.grab_report_card_value('r_squared')))
        if args.input is not None:
            output.write(output.grab_report_card_value('input_top_performers'))
            input_1_statement = 'The users list number one performer is ' + output.grab_report_card_value('input_1') + "."
            output.write(input_1_statement)
        if args.research:
            output.write(output.grab_report_card_value('research_top_performers'))
            research_1_statement = 'The research list number one performer is ' + output.grab_report_card_value('research_1') + "."
            output.write(research_1_statement)
        output.write("See below for the respective top performers tables and the top performer charts.")
        # now we include the tables
        if args.input is not None:
            table_data = input_manager.read_table(output.grab_report_card_value('input_sheet_name'))
            output.write_table(table_data, "User Input Stocks Performance Metric")
        if args.research is not None:
            table_data = input_manager.read_table(output.grab_report_card_value('research_sheet_name'))
            output.write_table(table_data, "Research Stocks Performance Metric")
        # now we include the plots
        if args.input is not None:
            output.add_plots_to_word(output.grab_report_card_value('input_1'), output.grab_report_card_value('input_figures'))
        if args.research:
            output.add_plots_to_word(output.grab_report_card_value('research_1'), output.grab_report_card_value('research_figures'))
        # Save file
        output.create_explanation_statement()
        output.save()

        if args.e:
            # email the output file to given email
            handler = OutputHandler(args.output)
            email_to = input("Email Recipient: ")
            username = input("Username: ")
            password = input("Password: ")
            logger.info(f"Sending Email to {email_to}")
            handler.email_file(email_to=email_to, smtp_username=username, smtp_password=password)
            logger.info("Email sent.")

if __name__ == "__main__":
    start_time = time.time()
    logger.info("Starting StockApp Program...")
    main()
    end_time = time.time()
    elapsed_time = end_time - start_time
    # Print the elapsed time
    logger.info("Program completed successfully.")
    logger.info(f"Program took {elapsed_time:.2f} seconds to run.")
