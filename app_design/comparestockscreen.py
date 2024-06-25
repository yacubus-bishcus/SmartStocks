# Imported Modules
import pandas as pd
from datetime import datetime
import logging
import matplotlib.pyplot as plt
import random
from tabulate import tabulate
import traceback
import threading

# Kivy Imported Modules
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.tooltip import MDTooltip
from kivymd.uix.behaviors import HoverBehavior
from kivymd.uix.button import MDIconButton
from kivy.properties import StringProperty, ObjectProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.uix.switch import Switch
from kivy.uix.gridlayout import GridLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivymd.uix.screen import MDScreen
from kivy.uix.checkbox import CheckBox
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Line, Rectangle, InstructionGroup
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.widget import Widget
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
from kivy.uix.spinner import Spinner
from kivy.uix.relativelayout import RelativeLayout
from kivy.core.window import Window
from kivy.lang import Builder
# My Imported Modules
from InputManager import StockInputManager
from ArgsParser import ArgsParser
from customoptions import CustomCheckBox, BackgroundColorBoxLayout
from Models import RSI, FIBONACCI, STOCHASTIC, MACD
from Stock import MyStock

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class TooltipMDIconButton(MDIconButton, HoverBehavior):
    tooltip_text = StringProperty('')

class CompareStocksScreen(MDScreen):
    def __init__(self, **kwargs):
        super(CompareStocksScreen, self).__init__(**kwargs)
        logger.info("Creating CompareStocksScreen Layout...")
        layout = BackgroundColorBoxLayout(orientation='vertical', padding=30, spacing=30)
        self.screen_width = Window.width
        self.screen_height = Window.height
        logger.info("CompareStocksScreen creating tooltip")

        self.tip_list = [
            "Fibonacci retracement. Levels—stemming from the Fibonacci sequence—are\n" \
            "horizontal lines that indicate where support and resistance are likely to occur.\n" \
            " Each level is associated with a percentage.\n" \
            " The percentage is how much of a prior move the price has retraced.\n" \
            " The Fibonacci retracement levels are 23.6%, 8.2%, 61.8%, and 78.6%.\n" \
            " While not officially a Fibonacci ratio, 50% is also used.\n" \
            " The indicator is useful because it can be drawn between any two\n" \
            " significant price points, such as a high and a low.\n", \
            "Index Comparison. A simple comparison either daily, 3mo or 6 months \n based on which respective calculation you choose.",
            "Moving Average Convergence-Divergence (MACD). When the MACD line \n crosses above the signal line, it indicates a bullish signal, suggesting it might be a good time to buy. Conversely, when the MACD line crosses below the signal line, it indicates a bearish signal, suggesting it might be a good time to sell.",
            "Relative Strength Index (RSI). As a momentum indicator, the relative \n strength index compares a security's strength on days when prices go up to its strength on days when prices go down. Relating the result of this comparison to price action can give traders an idea of how a security may perform. Traditionally the RSI is considered overbought when above 70 and oversold when below 30.",
            "Stochastic Oscillator. Measures the current price relative to the price \n range over a number of periods. Plotted between zero and 100, the idea is that the price should make new highs when the trend is up. In a downtrend, the price tends to make new lows."
        ]

        self.tooltip_button = TooltipMDIconButton(icon='information', tooltip_text=random.choice(self.tip_list))
        self.tooltip_button.bind(on_enter=self.on_tooltip_enter, on_leave=self.on_tooltip_leave)
        layout.add_widget(self.tooltip_button)
        # Creating the centered layout for tooltip label and highlighted box
        centered_layout_tooltip = FloatLayout(pos_hint={"center_x": 0.5, "top": 1}, size_hint=(None, None), size=(300, 100))
        self.tooltip_label = Label(text="", size_hint=(None, None), size=(300, 100), color=(0, 0, 0, 1))
        self.tooltip_label.opacity = 0  # Initially invisible

        # Title
        title_label = Label(text="Compare Stocks", font_size='64sp', size_hint=(1, None), height=50, color=(0, 0, 0, 1))
        layout.add_widget(title_label)

        # Spacer
        layout.add_widget(Widget(size_hint_y=None, height=5))

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

        # Switch for Clear Plots
        clear_plots_layout = BoxLayout(orientation='vertical', size_hint=(None, None), size=(300, 150))
        clear_plots_label = Label(text="Clear Plots", font_size='24sp', size_hint=(None, None), size=(300, 50), color=(0, 0, 0, 1))

        self.clear_plots_switch = Switch(active=False, size_hint=(None, None), size=(300, 50))
        self.clear_plots_switch.bind(active=self.on_clear_plots_switch_active)

        clear_plots_layout.add_widget(clear_plots_label)
        clear_plots_layout.add_widget(self.clear_plots_switch)

        centered_layout_clear_plots = AnchorLayout(anchor_x='center')
        centered_layout_clear_plots.add_widget(clear_plots_layout)
        layout.add_widget(centered_layout_clear_plots)

        # Back Button
        back_button_layout = AnchorLayout(anchor_x='right', anchor_y='bottom')
        back_button = Button(text="Back to Menu", size_hint=(None, None), size=(200, 50), color=(0, 0, 0, 1))
        back_button.bind(on_press=self.back_to_menu)
        back_button_layout.add_widget(back_button)
        layout.add_widget(back_button_layout)

        self.add_widget(layout)
        # has to be after add_widget(layout)
        centered_layout_tooltip.add_widget(self.tooltip_label)
        self.add_widget(centered_layout_tooltip)

        self.tooltip_text = random.choice(self.tip_list)
        Window.bind(mouse_pos=self.on_mouse_pos)

    def on_mouse_pos(self, *args):
        pos = args[1]
        if self.tooltip_button.collide_point(*self.tooltip_button.to_widget(*pos)):
            self.tooltip_label.text = self.tooltip_text
            self.tooltip_label.opacity = 1
            self.tooltip_label.center_x = self.tooltip_button.center_x
            self.tooltip_label.top = self.tooltip_button.y
        else:
            self.tooltip_label.opacity = 0

    def on_tooltip_enter(self, instance):
        self.tooltip_text = random.choice(self.tip_list)

    def on_tooltip_leave(self, instance):
        pass

    def on_clear_plots_switch_active(self, instance, value):
        if value:
            logger.info("Switch is ON - Clear Plots")
            self.manager.get_screen('compare_stocks_output').clear_plots()
            # Add your clear plots logic here
        else:
            logger.info("Switch is OFF - Keep Plots")
            # Add your keep plots logic here

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
        recommendations = input_instance.grab_recommendations()

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
        self.manager.current = 'compare_stocks_output'
        compare_output_screen.update_output(output_text, recommendations, plot_data, stocks, market_data, self.model_spinner.text, '1d')
        #self.manager.current = 'compare_stocks_output'

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
        recommendations = input_instance.grab_recommendations()

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
        compare_output_screen.update_output(output_text, recommendations, plot_data, stocks, market_data, self.model_spinner.text, '3mo')
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
        recommendations = input_instance.grab_recommendations()

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
        compare_output_screen.update_output(output_text, recommendations, plot_data, stocks, market_data, self.model_spinner.text, '6mo')
        self.manager.current = 'compare_stocks_output'

    def back_to_menu(self, instance):
        self.manager.current = 'menu'


class CompareStocksOutputScreen(MDScreen):
    def __init__(self, **kwargs):
        super(CompareStocksOutputScreen, self).__init__(**kwargs)
        self.create_layout()

    def create_layout(self):
        layout = BackgroundColorBoxLayout(orientation='vertical', padding=30, spacing=30)

        # Insert a banner area at the top
        self.stock_label = Label(text='Stock Information will be displayed here.', font_size='36sp', size_hint_y=0.05, color=(0,0,0,1))
        layout.add_widget(self.stock_label)
        self.plot_area = BoxLayout(size_hint_y=0.75)
        layout.add_widget(self.plot_area)

        self.output_label = Label(text="Output will be displayed here.", font_size='16sp', size_hint_y=0.05, color=(0,0,0,1)) # change to 0.10 once we add table of information
        layout.add_widget(self.output_label)
        self.output_label2 = Label(text="Recommendations Table will be displayed here.", font_size='14sp', size_hint_y=0.15, color=(0,0,0,1)) # change to 0.10 once we add table of information
        layout.add_widget(self.output_label2)

        self.back_button = Button(text="Back to Compare Stocks", size_hint_y=0.05)
        self.back_button.bind(on_press=self.back_to_compare)
        layout.add_widget(self.back_button)

        self.add_widget(layout)


    def back_to_compare(self, instance):
        self.manager.current = 'compare_stocks'

    def clear_plots(self):
        self.plot_area.clear_widgets()

    # Function to add padding to column headers
    def pad_headers(self, headers, pad=0):
        return [f' {header} '.center(len(header) + pad) for header in headers]

    # Function to pad DataFrame cells
    def pad_dataframe(self, df, pad=50):
        return df.applymap(lambda x: f' {str(x)} '.center(len(str(x)) + pad))

    def start_calculation_thread(self, instance):
        # Start a new thread for the calculation
        calculation_thread = threading.Thread(target=self.update_output)
        calculation_thread.start()

    def calculation_complete(self):
        logger.info(f"Compare Stocks Calculations are complete!")
        # Update the UI to reflect that the calculations are complete

    def update_output(self, output_text, recommendation_info, plot_data, stocks, indexes, model, time_period='1mo'):
        try:
            my_stocks = [MyStock(stock, time_period=time_period) for stock in stocks]
            stock_info_string = f"{my_stocks[0].name} ({my_stocks[0].symbol})  ${my_stocks[0].price} ({round(my_stocks[0].daily_percent, 2)})"

            # Determine color based on daily percent value
            if my_stocks[0].daily_percent < 0:
                text_color = (255,0,0,1)  # Red if negative
            else:
                text_color = (0,255,0,1)  # Green if positive

            # Update label text and color
            self.stock_label.text = stock_info_string
            self.stock_label.color = text_color

            if model == "Index Comparison":
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
                fibo = FIBONACCI(myStock_list=my_stocks, time_period=time_period) # defaults to 1mo for now
                fibo.execute_model()
                fig = fibo.plot()
            elif model == "MACD":
                macd = MACD(myStock_list=my_stocks, time_period=time_period) # defaults to 1mo for now
                macd.execute_model()
                fig = macd.plot()
            elif model == "RSI":
                rsi = RSI(myStock_list=my_stocks, time_period=time_period)
                rsi.execute_model()
                fig = rsi.plot()
            elif model == "Stochastic":
                stoch = STOCHASTIC(myStock_list=my_stocks, time_period=time_period)
                stoch.execute_model()
                fig = stoch.plot()

            self.plot_area.add_widget(FigureCanvasKivyAgg(fig))
            # Updating output label
            self.output_label.text = output_text if isinstance(output_text, str) else str(output_text)
            print("output_label updated:", self.output_label.text)

            recommendation_df = pd.DataFrame(recommendation_info)
            # New headers
            new_headers = ['Period', '+Buy', 'Buy', 'Hold', 'Sell', 'Strong Sell']
            # Rename the columns to the new headers
            recommendation_df.columns = new_headers
            padded_headers = self.pad_headers(recommendation_df.columns)
            padded_df = self.pad_dataframe(recommendation_df)
            recommendation_string = tabulate(padded_df, headers=padded_headers, tablefmt='plain', numalign='right', stralign='left', showindex=False)
            self.output_label2.text = recommendation_string
            print("output_label2 updated:", self.output_label2.text)

        except Exception as e:
            print(f"Exception in update_output: {e}")
            traceback.print_exc()
            self.output_label.text = f"An error occurred: {e}"

        # Update the UI from the main thread
        Clock.schedule_once(lambda dt: self.calculation_complete())
