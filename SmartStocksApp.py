import os

# Suppress Kivy logging messages
os.environ['KIVY_LOG_MODE'] = 'PYTHON'
from kivy.config import Config
# Set the default window size
Config.set('graphics', 'width', '1000')
Config.set('graphics', 'height', '1000')
Config.set('kivy', 'log_level', 'warning')

# Configure your own logger

from kivy.logger import Logger, LOG_LEVELS
Logger.setLevel(LOG_LEVELS["warning"])

import logging
# Ensure logging.basicConfig is not called after setting the level for your logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.checkbox import CheckBox
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Line, Rectangle
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.widget import Widget
#from garden.garden.matplotlib.backend_kivyagg import backend_kivyagg
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib.pyplot as plt
from .InputManager import StockInputManager
from .ArgsParser import ArgsParser
import pandas as pd
from datetime import datetime

class BackgroundColorBoxLayout(BoxLayout):
    def __init__(self, **kwargs):
        super(BackgroundColorBoxLayout, self).__init__(**kwargs)
        with self.canvas.before:
            Color(0.68, 0.85, 0.90, 1)  # Light blue color
            self.rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self._update_rect, pos=self._update_rect)

    def _update_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos

class CustomCheckBox(BoxLayout):
    def __init__(self, **kwargs):
        super(CustomCheckBox, self).__init__(**kwargs)

        # Create the internal CheckBox widget
        self.checkbox = CheckBox()
        self.add_widget(self.checkbox)

        # Create the outline for the CheckBox
        with self.checkbox.canvas.before:
            Color(0, 0, 0, 1)  # Black color for the outline
            self.outline = Line(rectangle=(self.checkbox.x, self.checkbox.y, self.checkbox.width, self.checkbox.height), width=1)

        # Bind update_outline method to position and size changes of checkbox
        self.checkbox.bind(pos=self.update_outline, size=self.update_outline)

        # Example initial state
        self.active = False

    def update_outline(self, *args):
        self.outline.rectangle = (self.checkbox.x, self.checkbox.y, self.checkbox.width, self.checkbox.height)

    # Define the 'active' property
    def _get_active(self):
        return self.checkbox.active

    def _set_active(self, value):
        self.checkbox.active = value
        self.update_outline()  # Update outline when active state changes

    active = property(_get_active, _set_active)


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        layout = BackgroundColorBoxLayout(orientation='vertical')

        # Title
        layout.add_widget(Label(text="Smart Stocks", font_size='48sp', size_hint=(1, 0.2), color=(0, 0, 0, 1)))

        # Image
        layout.add_widget(Image(source='logo.png', size_hint=(1, 0.3)))

        # Username Input
        username_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.1))
        username_layout.add_widget(Label(text="Username:", size_hint=(0.3, 1), color=(0, 0, 0, 1)))
        self.username_input = TextInput(size_hint=(0.7, 1))
        username_layout.add_widget(self.username_input)
        layout.add_widget(username_layout)

        # Password Input
        password_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.1))
        password_layout.add_widget(Label(text="Password:", size_hint=(0.3, 1), color=(0, 0, 0, 1)))
        self.password_input = TextInput(password=True, size_hint=(0.7, 1))
        password_layout.add_widget(self.password_input)
        layout.add_widget(password_layout)

        # Login Button
        login_button = Button(text="Login", size_hint=(1, 0.1))
        login_button.bind(on_press=self.login)
        layout.add_widget(login_button)

        # Create Account Button
        create_account_button = Button(text="Create Account", size_hint=(1, 0.1))
        create_account_button.bind(on_press=self.create_account)
        layout.add_widget(create_account_button)

        self.add_widget(layout)

    def login(self, instance):
        # For simplicity, let's just navigate to the menu screen on any login attempt
        self.manager.current = 'menu'

    def create_account(self, instance):
        print("Create Account option selected")
        # Navigate to a create account screen or handle account creation

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super(MenuScreen, self).__init__(**kwargs)
        layout = BackgroundColorBoxLayout(orientation='vertical')

        # Title
        layout.add_widget(Label(text="Main Menu", font_size='24sp', size_hint=(1, 0.2)))

        # Create A Report Button
        create_report_button = Button(text="Create A Report", size_hint=(1, 0.2))
        create_report_button.bind(on_press=self.create_report)
        layout.add_widget(create_report_button)

        # Schedule Reports Button
        schedule_reports_button = Button(text="Schedule Reports", size_hint=(1, 0.2))
        schedule_reports_button.bind(on_press=self.schedule_reports)
        layout.add_widget(schedule_reports_button)

        # Compare Stocks Button
        compare_stocks_button = Button(text="Compare Stocks", size_hint=(1, 0.2))
        compare_stocks_button.bind(on_press=self.compare_stocks)
        layout.add_widget(compare_stocks_button)

        # DayTrader Button
        daytrader_button = Button(text="DayTrader", size_hint=(1, 0.2))
        daytrader_button.bind(on_press=self.daytrader)
        layout.add_widget(daytrader_button)

        self.add_widget(layout)

    def create_report(self, instance):
        print("Create A Report option selected")

    def schedule_reports(self, instance):
        print("Schedule Reports option selected")

    def compare_stocks(self, instance):
        self.manager.current = 'compare_stocks'

    def daytrader(self, instance):
        print("DayTrader option selected")

class CompareStocksScreen(Screen):
    def __init__(self, **kwargs):
        super(CompareStocksScreen, self).__init__(**kwargs)
        layout = BackgroundColorBoxLayout(orientation='vertical', padding=20, spacing=10)

        # Title
        title_label = Label(text="Compare Stocks", font_size='64sp', size_hint=(1, None), height=50, color=(0, 0, 0, 1))
        layout.add_widget(title_label)

        # Spacer
        layout.add_widget(Widget(size_hint_y=None, height=5))
        # Centered Box Layout for Stock 1 Input
        stock1_layout = BoxLayout(orientation='vertical', size_hint=(None, None), size=(300, 100), spacing=2)
        stock_ticker_label = Label(text="Stock Ticker", font_size='36sp', size_hint=(None, None), size=(300, 100), color=(0, 0, 0, 1))
        stock1_layout.add_widget(stock_ticker_label)
        self.stock1_input = TextInput(size_hint=(None, None), size=(300, 50))
        stock1_layout.add_widget(self.stock1_input)

        # Spacer
        layout.add_widget(Widget(size_hint_y=None, height=5))
        # Center stock1_layout
        centered_layout_stock1 = AnchorLayout(anchor_x='center')
        centered_layout_stock1.add_widget(stock1_layout)
        layout.add_widget(centered_layout_stock1)

        # Centered Box Layout for Index Checkboxes
        indices_layout = BoxLayout(orientation='horizontal', size_hint=(None, None), size=(300, 100), spacing=40)

        sp500_layout = BoxLayout(orientation='horizontal', size_hint=(None, None), size=(90,30), spacing=2)
        self.sp500_checkbox = CustomCheckBox(size_hint=(None, None), size=(30,30))
        sp500_layout.add_widget(self.sp500_checkbox)
        sp500_layout.add_widget(Label(text="S&P500", size_hint=(None, None), size=(120,30), color=(0, 0, 0, 1)))
        indices_layout.add_widget(sp500_layout)

        nasdaq_layout = BoxLayout(orientation='horizontal', size_hint=(None, None), size=(90,30), spacing=2)
        self.nasdaq_checkbox = CustomCheckBox(size_hint=(None, None), size=(30,30))
        nasdaq_layout.add_widget(self.nasdaq_checkbox)
        nasdaq_layout.add_widget(Label(text="Nasdaq", size_hint=(None, None), size=(120,30), color=(0, 0, 0, 1)))
        indices_layout.add_widget(nasdaq_layout)

        dow_jones_layout = BoxLayout(orientation='horizontal', size_hint=(None, None), size=(90,30), spacing=2)
        self.dow_jones_checkbox = CustomCheckBox(size_hint=(None, None), size=(30,30))
        dow_jones_layout.add_widget(self.dow_jones_checkbox)
        dow_jones_layout.add_widget(Label(text="Dow Jones", size_hint=(None, None), size=(120,30), color=(0, 0, 0, 1)))
        indices_layout.add_widget(dow_jones_layout)

        # Center indices_layout
        centered_layout_indices = AnchorLayout(anchor_x='center', anchor_y='center')
        centered_layout_indices.add_widget(indices_layout)
        layout.add_widget(centered_layout_indices)

        # Compare Buttons
        compare_buttons_layout = BoxLayout(orientation='horizontal', size_hint=(None, None), size=(1500, 150), height=50, spacing=20)

        compare_daily_button = Button(text="Compare Daily", size_hint=(None, None), size=(500,100), color=(0, 0, 0, 1))
        compare_daily_button.bind(on_press=self.compare_daily)
        compare_buttons_layout.add_widget(compare_daily_button)

        compare_50day_button = Button(text="Compare 50 Day Average", size_hint=(None, None), size=(500,100), color=(0, 0, 0, 1))
        compare_50day_button.bind(on_press=self.compare_50day)
        compare_buttons_layout.add_widget(compare_50day_button)

        compare_200day_button = Button(text="Compare 200 Day Average", size_hint=(None, None), size=(500,100), color=(0, 0, 0, 1))
        compare_200day_button.bind(on_press=self.compare_200day)
        compare_buttons_layout.add_widget(compare_200day_button)

        # Center compare_buttons_layout
        centered_layout_buttons = AnchorLayout(anchor_x='center', anchor_y='center')
        centered_layout_buttons.add_widget(compare_buttons_layout)
        layout.add_widget(centered_layout_buttons)

        # Output Label
        self.output_label = Label(text="", font_size='24sp', size_hint=(1, None), height=50, color=(0, 0, 0, 1))
        layout.add_widget(self.output_label)

        # Back Button
        back_button = Button(text="Back to Menu", size_hint=(1, None), height=50, color=(0, 0, 0, 1))
        back_button.bind(on_press=self.back_to_menu)
        layout.add_widget(back_button)

        self.add_widget(layout)

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
        compare_output_screen.update_output(output_text, summary_info, plot_data, stocks, market_data)
        self.manager.current = 'compare_stocks_output'

    def compare_50day(self, instance):
        input_instance = StockInputManager(True)
        parser = ArgsParser()
        args = None
        if self.dow_jones_checkbox.active:
            args=parser.parse_args(f"--ticker {self.stock1_input.text} --c_50_Dow --summary")
        elif self.nasdaq_checkbox.active:
            args=parser.parse_args(f"--ticker {self.stock1_input.text} --c_50_Nas --summary")
        elif self.sp500_checkbox.active:
            args=parser.parse_args(f"--ticker {self.stock1_input.text} --c_50_Sap --summary")

        output = None
        self.input.set_args(args)
        self.output_label.text = str(input_instance.apply_input_conditions(args=args))

    def compare_200day(self, instance):
        self.output_label.text = "200 Day Average comparison data displayed here."
        self.output_label.text = "50 Day Average comparison data displayed here."
        args = None
        if self.dow_jones_checkbox.active:
            args=parser.parse_args(f"--ticker {self.stock1_input.text} --c_200_Dow")
        elif self.nasdaq_checkbox.active:
            args=parser.parse_args(f"--ticker {self.stock1_input.text} --c_200_Nas")
        elif self.sp500_checkbox.active:
            args=parser.parse_args(f"--ticker {self.stock1_input.text} --c_200_Sap")

        output = None
        self.input.set_args(args)
        self.output_label.text = str(input_instance.apply_input_conditions(args=args))

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

    def update_output(self, output_text, summary_info, plot_data, stocks, indexes):
        self.output_label.text = output_text
        #self.output_label2.text = summary_info
        self.plot_area.clear_widgets()

        fig, ax = plt.subplots(figsize=(20,12))
        df = pd.DataFrame(plot_data)
        df = df.T
        #df.index = df.index.date
        df.columns = [stock.info.get('longName') for stock in stocks]
        ax.plot(df.index, df.values, label=df.columns)
        ax.set_xlabel("Date/Time")
        ax.set_ylabel("Price")
        ax.legend(loc='upper left')

        df2 = pd.DataFrame(indexes)
        df2['Time'] = df2.index
        df2['Time'] = pd.to_datetime(df2['Time'])
        df2.set_index('Time', inplace=True)
        #df2.index = df.index.date
        df2.columns = ['Market Price']
        ax2 = ax.twinx()
        ax2.plot(df2.index, df2.values, label=df2.columns, color='black', linestyle='--')
        ax2.set_ylabel("Index Price")
        ax2.legend(loc='upper right')
        title_string = "Your Stock vs Market Price"
        plt.title(title_string)
        fig.autofmt_xdate()
        self.plot_area.add_widget(FigureCanvasKivyAgg(fig))


class SmartStocksApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='Smart Stocks'))
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(CompareStocksScreen(name='compare_stocks'))
        self.compare_screen = CompareStocksOutputScreen(name='compare_stocks_output')
        #self.compare_screen.display_table(data)
        sm.add_widget(self.compare_screen)

        return sm
