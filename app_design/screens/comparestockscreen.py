# Imported Modules
import logging
import threading

# Kivy Imported Modules
from kivymd.uix.screen import MDScreen
from kivy.properties import ObjectProperty
from kivy.clock import Clock

# My Imported Modules
from SmartStocksInputManager import SmartStocksInputManager
from ArgsParser import ArgsParser

logger = logging.getLogger(__name__)

class CompareStocksScreen(MDScreen):
    ticker_input = ObjectProperty(None) 
    dow_jones_checkbox = ObjectProperty(None)
    sp500_checkbox = ObjectProperty(None)
    nasdaq_checkbox = ObjectProperty(None)
    model_spinner = ObjectProperty(None)
    clear_plots_switch = ObjectProperty(None)
    calculation_label = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = self.theme_cls.bg_normal 

    def on_clear_plots_switch_active(self):
        if self.clear_plots_switch.active:
            logger.info("Switch is ON - Clear Plots")
            self.manager.get_screen('compare_stocks_output').clear_plots()

    def show_calculation_label(self, *args):
        self.calculation_label.opacity = 1

    def hide_calculation_label(self, *args):
        self.calculation_label.opacity = 0

    def conduct_analysis(self, input_instance, args):
        input_instance.tickers = (self.ticker_input.text, None, None, None) 
        input_instance.stocks = (input_instance.tickers) 
        results = input_instance.apply_input_conditions(args=args)
        return_string, stock_obj, market_data = results
        market_data = market_data['Close'] 
        output_text = str(return_string)
        recommendations = input_instance.grab_recommendations()
        if not isinstance(stock_obj, list):
            stock_obj = [stock_obj]

        compare_output_screen = self.manager.get_screen('compare_stocks_output')
        
        # Schedule the update_output call on the main thread
        Clock.schedule_once(lambda dt: compare_output_screen.update_output(output_text=output_text, 
                                                                       recommendations=recommendations, 
                                                                       stocks=stock_obj, 
                                                                       market_data=market_data, 
                                                                       model=self.model_spinner.text))
        
        Clock.schedule_once(lambda dt: self.hide_calculation_label())
        Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'compare_stocks_output'))

    def compare_daily(self):
        Clock.schedule_once(self.show_calculation_label)
        input_instance = SmartStocksInputManager()
        parser = ArgsParser()
        args = None
        ticker_list = [ticker.strip() for ticker in self.ticker_input.text.split(',')]  # Assuming tickers are comma-separated
        if self.dow_jones_checkbox.active:
            args = parser.parse_args(f"--ticker {','.join(ticker_list)} --compare_index --index ^DJI --model_period 1d --model_interval 5m -r")
            logger.info(f"Your ticker: {args.ticker}")
            logger.debug("Pushed dow jones.")
        elif self.nasdaq_checkbox.active:
            args = parser.parse_args(f"--ticker {','.join(ticker_list)}  --compare_index --index ^IXIC --model_period 1d --model_interval 5m -r")
            logger.info(f"Your ticker: {args.ticker}")
            logger.debug("Pushed nasdaq")
        elif self.sp500_checkbox.active:
            args = parser.parse_args(f"--ticker {','.join(ticker_list)} --compare_index --index ^GSPC --model_period 1d --model_interval 5m -r")
            logger.info(f"Your ticker: {args.ticker}")
            logger.debug("Pushed S&P")

        # Perform analysis and schedule UI update on main thread
        calculation_thread = threading.Thread(target=self.conduct_analysis, args=(input_instance, args))
        calculation_thread.start()

    def compare_50day(self):
        Clock.schedule_once(self.show_calculation_label)
        input_instance = SmartStocksInputManager()
        parser = ArgsParser()
        args = None
        ticker_list = [ticker.strip() for ticker in self.ticker_input.text.split(',')]  # Assuming tickers are comma-separated
        if self.dow_jones_checkbox.active:
            args = parser.parse_args(f"--ticker {','.join(ticker_list)} --compare_index_50 --index ^DJI --model_period 3mo --model_interval 1d -r")
            logger.info(f"Your ticker: {args.ticker}")
            logger.debug("Pushed dow jones.")
        elif self.nasdaq_checkbox.active:
            args = parser.parse_args(f"--ticker {','.join(ticker_list)}  --compare_index_50 --index ^IXIC --model_period 3mo --model_interval 1d -r")
            logger.info(f"Your ticker: {args.ticker}")
            logger.debug("Pushed nasdaq")
        elif self.sp500_checkbox.active:
            args = parser.parse_args(f"--ticker {','.join(ticker_list)} --compare_index_50 --index ^GSPC --model_period 3mo --model_interval 1d -r")
            logger.info(f"Your ticker: {args.ticker}")
            logger.debug("Pushed S&P")

        # Perform analysis and schedule UI update on main thread
        calculation_thread = threading.Thread(target=self.conduct_analysis, args=(input_instance, args))
        calculation_thread.start()

    def compare_200day(self):
        Clock.schedule_once(self.show_calculation_label)
        input_instance = SmartStocksInputManager()
        parser = ArgsParser()
        args = None
        ticker_list = [ticker.strip() for ticker in self.ticker_input.text.split(',')]  # Assuming tickers are comma-separated
        if self.dow_jones_checkbox.active:
            args = parser.parse_args(f"--ticker {','.join(ticker_list)} --compare_index_200 --index ^DJI --model_period 6mo --model_interval 1d -r")
            logger.info(f"Your ticker: {args.ticker}")
            logger.debug("Pushed dow jones.")
        elif self.nasdaq_checkbox.active:
            args = parser.parse_args(f"--ticker {','.join(ticker_list)}  --compare_index_200 --index ^IXIC --model_period 6mo --model_interval 1d -r")
            logger.info(f"Your ticker: {args.ticker}")
            logger.debug("Pushed nasdaq")
        elif self.sp500_checkbox.active:
            args = parser.parse_args(f"--ticker {','.join(ticker_list)} --compare_index_200 --index ^GSPC --model_period 6mo --model_interval 1d -r")
            logger.info(f"Your ticker: {args.ticker}")
            logger.debug("Pushed S&P")

        # Perform analysis and schedule UI update on main thread
        calculation_thread = threading.Thread(target=self.conduct_analysis(input_instance, args))
        calculation_thread.start()

    def back_to_menu(self):
        self.manager.current = 'menu'

    def calculation_complete(self):
        logger.info(f"Compare Stocks Calculations are complete!")
        Clock.schedule_once(self.hide_calculation_label)