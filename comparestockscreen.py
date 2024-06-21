# Imported Modules
import pandas as pd
from datetime import datetime
import logging
import matplotlib.pyplot as plt
import random

# Kivy Imported Modules
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.checkbox import CheckBox
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Line, Rectangle
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.widget import Widget
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
from kivy.uix.spinner import Spinner
from kivy.uix.relativelayout import RelativeLayout
from kivy.core.window import Window
# My Imported Modules
from .InputManager import StockInputManager
from .ArgsParser import ArgsParser
from .customoptions import CustomCheckBox, BackgroundColorBoxLayout
from .Models import RSI, FIBONACCI, STOCHASTIC, MACD
from .Stock import MyStock

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)



class CompareStocksScreen(Screen):
    def __init__(self, **kwargs):
        super(CompareStocksScreen, self).__init__(**kwargs)
        layout = BackgroundColorBoxLayout(orientation='vertical', padding=30, spacing=30)
        self.screen_width = Window.width
        self.screen_height = Window.height

        # Tooltip Section (Top Left)
        tooltip_layout = AnchorLayout(anchor_x='left', anchor_y='top')
        fibo_tip = """
            Smart Stocks Tip:
            - Fibonacci retracement. Levels—stemming from the Fibonacci
            sequence—are horizontal lines that indicate where support and
            resistance are likely to occur.
            Each level is associated with a percentage.
            The percentage is how much of a prior move the price has retraced.
            The Fibonacci retracement levels are 23.6%, 8.2%, 61.8%, and 78.6%.
            While not officially a Fibonacci ratio, 50% is also used.
            The indicator is useful because it can be drawn between any two
            significant price points, such as a high and a low.
        """
        index_tip = """
            Smart Stocks Tip:
            - Index Comparison. A simple comparison either daily, 3mo or 6 months
            based on which respective calculation you choose.
        """
        macd_tip = """
            Smart Stocks Tip:
            - Moving Average Convergence-Divergence (MACD). When the MACD line
            crosses above the signal line, it indicates a bullish signal,
            suggesting it might be a good time to buy. Conversely, when
            the MACD line crosses below the signal line, it indicates a bearish
            signal, suggesting it might be a good time to sell.
        """
        rsi_tip = """
            Smart Stocks Tip:
            - Relative Strength Index (RSI). As a momentum indicator, the
            relative strength index compares a security's strength on days
            when prices go up to its strength on days when prices go down.
            Relating the result of this comparison to price action can give
            traders an idea of how a security may perform. Traditionally the
            RSI is considered overbought when above 70 and oversold
            when below 30.
        """
        stoch_tip = """
            Smart Stocks Tip:
            - Stochastic Oscillator. Measures the current price relative to the price range
            over a number of periods. Plotted between zero and 100, the idea is that the
            price should make new highs when the trend is up. In a downtrend, the price
            tends to make new lows.
        """

        tip_list = [fibo_tip, index_tip, macd_tip, rsi_tip, stoch_tip]
        random_index = random.randint(0,4)
        just_the_tip = tip_list[random_index]


        # Title
        title_label = Label(text="Compare Stocks", font_size='64sp', size_hint=(1, None), height=50, color=(0, 0, 0, 1))
        layout.add_widget(title_label)

        # Spacer
        layout.add_widget(Widget(size_hint_y=None, height=5))


        tooltip_layout = AnchorLayout(anchor_x='left', anchor_y='top')
        self.tooltip_label = Label(
            text=just_the_tip,
            font_size='20sp',
            size_hint=(None, None),
            size=(self.screen_width / 3, 150),
            pos_hint={'x': 0.05, 'top': 1},
            color=(0, 0, 0, 1)
        )
        tooltip_layout.add_widget(self.tooltip_label)
        layout.add_widget(tooltip_layout)


        # Centered Box Layout for Stock Ticker Input
        stock1_layout = BoxLayout(orientation='vertical', size_hint=(None, None), size=(300, 100), spacing=2)
        stock_ticker_label = Label(text="Stock Ticker", font_size='36sp', size_hint=(None, None), size=(300, 100), color=(0, 0, 0, 1))
        stock1_layout.add_widget(stock_ticker_label)
        self.stock1_input = TextInput(size_hint=(None, None), size=(300, 50))
        stock1_layout.add_widget(self.stock1_input)
        centered_layout_stock1 = AnchorLayout(anchor_x='center')
        centered_layout_stock1.add_widget(stock1_layout)
        layout.add_widget(centered_layout_stock1)

        # Spacer
        layout.add_widget(Widget(size_hint_y=None, height=5))

        # Dropdown Menu for Models with Label
        model_layout = BoxLayout(orientation='vertical', size_hint=(None, None), size=(300, 50), spacing=10)
        model_label = Label(text="Choose Model to Plot", font_size='24sp', size_hint=(None, None), size=(300, 50), color=(0, 0, 0, 1))
        model_layout.add_widget(model_label)
        models = ["Fibonacci Retracement", "Index Comparison", "MACD", "RSI", "Stochastic"]
        self.model_spinner = Spinner(
            text='Select Model',
            values=models,
            size_hint=(None, None),
            size=(300, 50),
            color=(0, 0, 0, 1)
        )
        model_layout.add_widget(self.model_spinner)
        centered_layout_spinner = AnchorLayout(anchor_x='center')
        centered_layout_spinner.add_widget(model_layout)
        layout.add_widget(centered_layout_spinner)

        # Spacer
        layout.add_widget(Widget(size_hint_y=None, height=10))

        # Centered Box Layout for Index Checkboxes with Label
        index_layout = BoxLayout(orientation='vertical', size_hint=(None, None), size=(400, 150), spacing=10)
        index_label = Label(text="Choose Index to Compare as Market Data", font_size='24sp', size_hint=(None, None), size=(400, 150), color=(0, 0, 0, 1))
        index_layout.add_widget(index_label)

        indices_layout = BoxLayout(orientation='horizontal', size_hint=(None, None), size=(330, 30), spacing=40)
        sp500_layout = BoxLayout(orientation='horizontal', size_hint=(None, None), size=(150, 30), spacing=2)
        self.sp500_checkbox = CustomCheckBox(size_hint=(None, None), size=(30, 30))
        sp500_layout.add_widget(self.sp500_checkbox)
        sp500_layout.add_widget(Label(text="S&P500", size_hint=(None, None), size=(120, 30), color=(0, 0, 0, 1)))
        indices_layout.add_widget(sp500_layout)

        nasdaq_layout = BoxLayout(orientation='horizontal', size_hint=(None, None), size=(150, 30), spacing=2)
        self.nasdaq_checkbox = CustomCheckBox(size_hint=(None, None), size=(30, 30))
        nasdaq_layout.add_widget(self.nasdaq_checkbox)
        nasdaq_layout.add_widget(Label(text="Nasdaq", size_hint=(None, None), size=(120, 30), color=(0, 0, 0, 1)))
        indices_layout.add_widget(nasdaq_layout)

        dow_jones_layout = BoxLayout(orientation='horizontal', size_hint=(None, None), size=(150, 30), spacing=2)
        self.dow_jones_checkbox = CustomCheckBox(size_hint=(None, None), size=(30, 30))
        dow_jones_layout.add_widget(self.dow_jones_checkbox)
        dow_jones_layout.add_widget(Label(text="Dow Jones", size_hint=(None, None), size=(120, 30), color=(0, 0, 0, 1)))
        indices_layout.add_widget(dow_jones_layout)

        index_layout.add_widget(indices_layout)
        centered_layout_indices = AnchorLayout(anchor_x='center', anchor_y='center')
        centered_layout_indices.add_widget(index_layout)
        layout.add_widget(centered_layout_indices)

        # Compare Buttons with Label
        compare_buttons_layout = BoxLayout(orientation='vertical', size_hint=(None, None), size=(1500, 200), spacing=20)

        buttons_layout = BoxLayout(orientation='horizontal', size_hint=(None, None), size=(1500, 150), height=40, spacing=20)
        compare_daily_button = Button(text="Compare Daily", font_size="20sp", size_hint=(None, None), size=(500, 100), color=(0, 0, 0, 1))
        compare_daily_button.bind(on_press=self.compare_daily)
        buttons_layout.add_widget(compare_daily_button)

        compare_50day_button = Button(text="Compare 50 Day Average", font_size="20sp",size_hint=(None, None), size=(500, 100), color=(0, 0, 0, 1))
        compare_50day_button.bind(on_press=self.compare_50day)
        buttons_layout.add_widget(compare_50day_button)

        compare_200day_button = Button(text="Compare 200 Day Average", font_size="20sp",size_hint=(None, None), size=(500, 100), color=(0, 0, 0, 1))
        compare_200day_button.bind(on_press=self.compare_200day)
        buttons_layout.add_widget(compare_200day_button)

        compare_buttons_layout.add_widget(buttons_layout)
        centered_layout_buttons = AnchorLayout(anchor_x='center', anchor_y='center')
        centered_layout_buttons.add_widget(compare_buttons_layout)
        layout.add_widget(centered_layout_buttons)

        # Back Button
        back_button_layout = AnchorLayout(anchor_x='right', anchor_y='bottom')
        back_button = Button(text="Back to Menu", size_hint=(None, None), size=(200, 50), color=(0, 0, 0, 1))
        back_button.bind(on_press=self.back_to_menu)
        back_button_layout.add_widget(back_button)
        layout.add_widget(back_button_layout)

        # # Loader (Bottom Left)
        # loader_layout = AnchorLayout(anchor_x='center', anchor_y='bottom')
        # self.loader_spinner = ThickerProgressBar(value=250, max=350)
        # self.loader_spinner.opacity = 0  # Initially hidden
        # loader_layout.add_widget(self.loader_spinner)
        # layout.add_widget(loader_layout)

        self.add_widget(layout)

    # def update_progress(self, current_step, total_steps):
    #     # Update the progress bar based on current step and total steps
    #     progress = (current_step + 1) / total_steps
    #     self.loader_spinner.value = progress * self.loader_spinner.max

    def compare_daily(self, instance):
        input_instance = StockInputManager(True)
        parser = ArgsParser()
        args = None
        ticker_list = [ticker.strip() for ticker in self.stock1_input.text.split(',')]  # Assuming tickers are comma-separated
        if self.dow_jones_checkbox.active:
            args = parser.parse_args(f"--ticker {','.join(ticker_list)} --c_Dow --model_time_delta 1d -r")
            logger.info(f"Your ticker: {args.ticker}")
            logger.debug("Pushed dow jones.")
        elif self.nasdaq_checkbox.active:
            args = parser.parse_args(f"--ticker {','.join(ticker_list)}  --c_Nas --model_time_delta 1d -r")
            logger.info(f"Your ticker: {args.ticker}")
            logger.debug("Pushed nasdaq")
        elif self.sp500_checkbox.active:
            args = parser.parse_args(f"--ticker {','.join(ticker_list)} --c_Sap --model_time_delta 1d -r")
            logger.info(f"Your ticker: {args.ticker}")
            logger.debug("Pushed S&P")

        output = None
        input_instance.set_args(args)
        output_text = str(input_instance.apply_input_conditions(args=args))
        summary_info = input_instance.grab_recommendations()

        stocks = input_instance.grab_stocks()
        if self.dow_jones_checkbox.active:
            the_index = "dow jones"
        elif self.nasdaq_checkbox.active:
            the_index = "nasdaq"
        elif self.sp500_checkbox.active:
            the_index = "s&p500"

        indexes = input_instance.grab_market_data(the_index, "1d")
        market_data = indexes['Close']

        plot_data = [stock.history(period="1d", interval='5m')['Close'] for stock in stocks]
        compare_output_screen = self.manager.get_screen('compare_stocks_output')
        compare_output_screen.update_output(output_text, summary_info, plot_data, stocks, market_data, self.model_spinner.text, '1d')
        self.manager.current = 'compare_stocks_output'

    def compare_50day(self, instance):
        input_instance = StockInputManager(True)
        parser = ArgsParser()
        args = None
        ticker_list = [ticker.strip() for ticker in self.stock1_input.text.split(',')]  # Assuming tickers are comma-separated
        if self.dow_jones_checkbox.active:
            args = parser.parse_args(f"--ticker {','.join(ticker_list)} --c_50_Dow_ --model_time_delta 3mo -r")
            logger.info(f"Your ticker: {args.ticker}")
            logger.debug("Pushed dow jones.")
        elif self.nasdaq_checkbox.active:
            args = parser.parse_args(f"--ticker {','.join(ticker_list)}  --c_50_Nas --model_time_delta 3mo -r")
            logger.info(f"Your ticker: {args.ticker}")
            logger.debug("Pushed nasdaq")
        elif self.sp500_checkbox.active:
            args = parser.parse_args(f"--ticker {','.join(ticker_list)} --c_50_Sap --model_time_delta 3mo -r")
            logger.info(f"Your ticker: {args.ticker}")
            logger.debug("Pushed S&P")

        output = None
        input_instance.set_args(args)
        output_text = str(input_instance.apply_input_conditions(args=args))
        summary_info = input_instance.grab_recommendations()

        stocks = input_instance.grab_stocks()
        if self.dow_jones_checkbox.active:
            the_index = "dow jones"
        elif self.nasdaq_checkbox.active:
            the_index = "nasdaq"
        elif self.sp500_checkbox.active:
            the_index = "s&p500"

        market = input_instance.grab_market_data(the_index, "3mo")
        market_data = market['Close']

        plot_data = [stock.history(period="3mo")['Close'] for stock in stocks]
        compare_output_screen = self.manager.get_screen('compare_stocks_output')
        compare_output_screen.update_output(output_text, summary_info, plot_data, stocks, market_data, self.model_spinner.text, '3mo')
        self.manager.current = 'compare_stocks_output'

    def compare_200day(self, instance):
        input_instance = StockInputManager(True)
        parser = ArgsParser()
        args = None
        ticker_list = [ticker.strip() for ticker in self.stock1_input.text.split(',')]  # Assuming tickers are comma-separated
        if self.dow_jones_checkbox.active:
            args = parser.parse_args(f"--ticker {','.join(ticker_list)} --c_200_Dow --model_time_delta 6mo -r")
            logger.info(f"Your ticker: {args.ticker}")
            logger.debug("Pushed dow jones.")
        elif self.nasdaq_checkbox.active:
            args = parser.parse_args(f"--ticker {','.join(ticker_list)}  --c_200_Nas --model_time_delta 6mo -r")
            logger.info(f"Your ticker: {args.ticker}")
            logger.debug("Pushed nasdaq")
        elif self.sp500_checkbox.active:
            args = parser.parse_args(f"--ticker {','.join(ticker_list)} --c_200_Sap --model_time_delta 6mo -r")
            logger.info(f"Your ticker: {args.ticker}")
            logger.debug("Pushed S&P")

        output = None
        input_instance.set_args(args)
        output_text = str(input_instance.apply_input_conditions(args=args))
        summary_info = input_instance.grab_recommendations()

        stocks = input_instance.grab_stocks()
        if self.dow_jones_checkbox.active:
            the_index = "dow jones"
        elif self.nasdaq_checkbox.active:
            the_index = "nasdaq"
        elif self.sp500_checkbox.active:
            the_index = "s&p500"

        indexes = input_instance.grab_market_data(the_index, "6mo")
        market_data = indexes['Close']

        plot_data = [stock.history(period="6mo")['Close'] for stock in stocks]
        compare_output_screen = self.manager.get_screen('compare_stocks_output')
        compare_output_screen.update_output(output_text, summary_info, plot_data, stocks, market_data, self.model_spinner.text, '6mo')
        self.manager.current = 'compare_stocks_output'

    def back_to_menu(self, instance):
        self.manager.current = 'menu'

    def build_args_from_gui(self):
        self.args = {}
        # Set all defaults
        self.args['c'] = False
        self.args['c_50'] = False
        self.args['c_200'] = False
        self.args['c_Dow'] = False
        self.args['c_Nas'] = False
        self.args['c_Sap'] = False
        self.args['c_50_Dow'] = False
        self.args['c_50_Nas'] = False
        self.args['c_c_50_Sap'] = False
        self.args['c_200_Dow'] = False
        self.args['c_200_Nas'] = False
        self.args['c_200_Sap'] = False
        self.args['co_200'] = False
        self.args['c_Daily'] = False
        self.args['data'] = ['nasdaqlisted.txt', 'otherlisted.txt']
        self.args['d'] = False
        self.args['e'] = False
        self.args['import_model_class'] = []
        self.args['import_model_module'] = []
        self.args['input'] = ''
        self.args['index'] = 's&p'
        self.args['jump_parameter'] = 1.
        self.args['max_price'] = "10000."
        self.args['models'] = ['Fifty Day','Two Hundred Day','CAPM', 'MACD', 'RSI', 'Stochastic']
        self.args['model_time_delta'] = "1mo"
        self.args['min_price'] = "1.00"
        self.args['number_to_highlight'] = '3'
        self.args['number_to_research'] = "10"
        self.args['output'] = None
        self.args['p'] = False
        self.args['price_processing_model'] = 'close_open'
        self.args['processes'] = 1
        self.args['r'] = False
        self.args['report'] = False
        self.args['research'] = False
        self.args['seed'] = 42
        self.args['sim_time'] = 30
        self.args['simulations'] = 0
        self.args['simulation_model'] = 'gaussian'
        self.args['summary'] = False
        self.args['ticker'] = None
        self.args['u'] = False
        self.args['weights'] = {'Fifty Day':0.1, 'Two Hundred Day':0.1, 'CAPM':0.2, 'MACD':0.05, 'RSI':0.3, 'Stochastic':0.25}

    def set_args_from_gui(self, the_arg, the_value):
        self.args[the_arg] = the_value

class CompareStocksOutputScreen(Screen):
    def __init__(self, **kwargs):
        super(CompareStocksOutputScreen, self).__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical')

        self.plot_area = BoxLayout(size_hint_y=0.75)
        self.layout.add_widget(self.plot_area)

        self.output_label = Label(text="Output will be displayed here.", size_hint_y=0.20) # change to 0.10 once we add table of information
        self.layout.add_widget(self.output_label)

        self.back_button = Button(text="Back to Compare Stocks", size_hint_y=0.05)
        self.back_button.bind(on_press=self.back_to_compare)
        self.layout.add_widget(self.back_button)

        self.add_widget(self.layout)


    def display_table(self, data):
        # Clear previous table
        self.layout.clear_widgets()

        # Add table headers
        headers = ["Stock", "Price", "Change", "Volume"]
        for header in headers:
            self.layout.add_widget(Label(text=header, bold=True))

        # Add data rows
        for row in data:
            for cell in row:
                self.layout.add_widget(Label(text=str(cell)))

    def back_to_compare(self, instance):
        self.manager.current = 'compare_stocks'

    def update_output(self, output_text, summary_info, plot_data, stocks, indexes, model, time_period='1mo'):
        self.output_label.text = output_text
        #self.output_label2.text = summary_info
        self.plot_area.clear_widgets()

        fig, ax = plt.subplots(figsize=(20,12))
        df = pd.DataFrame(plot_data)
        df = df.T
        #df.index = df.index.date
        df.columns = [stock.info.get('longName') for stock in stocks]
        df2 = pd.DataFrame(indexes)
        df2['Time'] = df2.index
        df2['Time'] = pd.to_datetime(df2['Time'])
        df2.set_index('Time', inplace=True)
        #df2.index = df.index.date
        df2.columns = ['Market Price']

        if model == "Index Comparison":
            ax.plot(df.index, df.values, label=df.columns)
            ax.set_xlabel("Date/Time")
            ax.set_ylabel("Price")
            ax.legend(loc='upper left')
            ax2 = ax.twinx()
            ax2.plot(df2.index, df2.values, label=df2.columns, color='black', linestyle='--')
            ax2.set_ylabel("Index Price")
            ax2.legend(loc='upper right')
            title_string = "Your Stock vs Market Price"
            plt.title(title_string)
            fig.autofmt_xdate()
        elif model == "Fibonacci Retracement":
            my_stocks = [MyStock(stock, time_period=time_period) for stock in stocks]
            fibo = FIBONACCI(myStock_list=my_stocks, time_period=time_period) # defaults to 1mo for now
            fibo.execute_model()
            fig = fibo.plot()
        elif model == "MACD":
            my_stocks = [MyStock(stock, time_period=time_period) for stock in stocks]
            macd = MACD(myStock_list=my_stocks, time_period=time_period) # defaults to 1mo for now
            macd.execute_model()
            fig = macd.plot()
        elif model == "RSI":
            my_stocks = [MyStock(stock, time_period=time_period) for stock in stocks]
            rsi = RSI(myStock_list=my_stocks, time_period=time_period)
            rsi.execute_model()
            fig = rsi.plot()
        elif model == "Stochastic":
            my_stocks = [MyStock(stock, time_period=time_period) for stock in stocks]
            stoch = STOCHASTIC(myStock_list=my_stocks, time_period=time_period)
            stoch.execute_model()
            fig = stoch.plot()

        self.plot_area.add_widget(FigureCanvasKivyAgg(fig))
