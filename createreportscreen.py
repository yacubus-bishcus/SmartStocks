# Imported Modules
import threading
import logging

# Kivy Imported Modules
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.properties import StringProperty, ObjectProperty, ListProperty, BooleanProperty
from kivymd.uix.button import MDRaisedButton
from kivy.base import runTouchApp
from kivy.app import App
from kivy.clock import Clock
from kivymd.uix.menu import MDDropdownMenu

# My Imported Modules
from InputManager import StockInputManager
from ArgsParser import ArgsParser

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class CheckItem(MDBoxLayout):
    text = StringProperty()
    group = StringProperty()
    active = BooleanProperty(False)

    def on_checkbox_active(self, instance, value):
        self.active = value
        print(f'{self.text} is {value}')

class CreateReportScreen(MDScreen):
    ticker_input = ObjectProperty(None)  # Add a reference to the ticker input
    dow_input = ObjectProperty(None)
    include_list = ObjectProperty(None)
    fifty_day_model = ObjectProperty(None)
    twohundred_day_model = ObjectProperty(None)
    capm_model = ObjectProperty(None)
    macd_model = ObjectProperty(None)
    rsi_model = ObjectProperty(None)
    stoch_model = ObjectProperty(None)
    weights_value = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(CreateReportScreen, self).__init__(**kwargs)
        self.md_bg_color = self.theme_cls.bg_normal  # Correct assignment
        self.add_back_to_menu_button()
        self.add_calculate_button()

    def init_dropdown_menu(self):
        menu_items = [
            {"viewclass": "OneLineListItem", "text": f"Item {i}", "height": dp(56),
             "on_release": lambda x=f"Item {i}": self.menu_callback(x)}
            for i in range(5)
        ]

        self.menu = MDDropdownMenu(
            caller=self.ids.index_dropdown,
            items=menu_items,
            width_mult=4
        )
    def init_dropdown_menu_model_time(self):
        menu_items = [
            {"viewclass": "OneLineListItem", "text": f"Item {i}", "height": dp(56),
             "on_release": lambda x=f"Item {i}": self.menu_callback_model_time(x)}
            for i in range(7)
        ]

        self.menu = MDDropdownMenu(
            caller=self.ids.model_time_dropdown,
            items=menu_items,
            width_mult=4
        )
    def menu_callback_model_time(self, text_item):
        self.ids.model_time_dropdown.set_item(text_item)
        self.menu.dismiss()

    def open_menu_model_time(self, item):
        menu_items = [
            {"text": "1d", "on_release": lambda x="1d": self.get_model_time_value(x)},
            {"text": "5d", "on_release": lambda x="5d": self.get_model_time_value(x)},
            {"text": "1mo", "on_release": lambda x="1mo": self.get_model_time_value(x)},
            {"text": "3mo", "on_release": lambda x="3mo": self.get_model_time_value(x)},
            {"text": "6mo", "on_release": lambda x="6mo": self.get_model_time_value(x)},
            {"text": "1y", "on_release": lambda x="1y": self.get_model_time_value(x)},
            {"text": "ytd", "on_release": lambda x="ytd": self.get_model_time_value(x)},
        ]
        MDDropdownMenu(caller=item, items=menu_items).open()

    def menu_callback(self, text_item):
        self.ids.index_dropdown.set_item(text_item)
        self.menu.dismiss()

    def open_menu(self, item):
        menu_items = [
            {"text": "S&P500", "on_release": lambda x="S&P500": self.get_index_value(x)},
            {"text": "NASDAQ", "on_release": lambda x="NASDAQ": self.get_index_value(x)},
            {"text": "DOW JONES", "on_release": lambda x="DOW JONES": self.get_index_value(x)},
        ]
        MDDropdownMenu(caller=item, items=menu_items).open()

    def back_to_menu(self, instance):
        self.manager.current = "menu"

    def add_back_to_menu_button(self):
        back_to_menu_button = MDRaisedButton(
            text="Back to Menu",
            size_hint=(None, None),
            size=(200,50),
            pos_hint= {"center_x":0.5},
            on_release=self.back_to_menu
        )
        self.ids.main_layout.add_widget(back_to_menu_button)

    def add_calculate_button(self):
        # Create a new button
        calculate_button = MDRaisedButton(
            text="Calculate",
            size_hint=(None, None),
            size=(200, 50),
            pos_hint={"center_x": 0.5},
            on_release=self.start_calculation_thread
        )

        # Add the button to the main layout
        self.ids.main_layout.add_widget(calculate_button)

    def get_ticker_value(self):
        ticker_value = self.ticker_input.text
        print(f"Ticker Value: {ticker_value}")  # Print the ticker value for debugging
        return ticker_value

    def get_use_dow_value(self):
        logger.info(f"Dow Value {self.dow_input.active}")
        if self.dow_input.active:
            return "-u"
        else:
            return ""

    def get_include_list_value(self):
        logger.info(f"Include List Value {self.include_list.active}")
        if self.include_list.active:
            return "--input MyStock.txt"
        else:
            return ""

    def get_index_value(self, index=""):
        logger.info(f"Index Value {index}")
        if index == "S&P500":
            self.index = "--index s&p"
            return self.index
        elif index == "NASDAQ":
            self.index = "--index nas"
            return self.index
        elif index == "DOW JONES":
            self.index = "--index dow"
            return self.index
        else:
            return ""

    def get_models_values(self):
        #['Fifty Day','Two Hundred Day','CAPM', 'MACD', 'RSI', 'Stochastic']
        model_list = []
        if self.fifty_day_model.active:
            model_list.append('Fifty Day')
        if self.twohundred_day_model.active:
            model_list.append("Two Hundred Day")
        if self.capm_model.active:
            model_list.append('CAPM')
        if self.macd_model.active:
            model_list.append('MACD')
        if self.rsi_model.active:
            model_list.append('RSI')
        if self.stoch_model.active:
            model_list.append('Stochastic')
        if model_list == []:
            return ""
        else:
            return f"--models [{model_list}]"

    def get_model_time_value(self, model_time):
        logger.info(f"Model Time Value {model_time}")
        if model_time == "1d":
            self.model_time = "--model_time_delta 1d"
            return self.model_time
        elif model_time == "5d":
            self.model_time = "--model_time_delta 5d"
            return self.model_time
        elif model_time == "1mo":
            self.model_time = "--model_time_delta 1mo"
            return self.model_time
        elif model_time == "3mo":
            self.model_time = "--model_time_delta 3mo"
            return self.model_time
        elif model_time == "6mo":
            self.model_time = "--model_time_delta 6mo"
            return self.model_time
        elif model_time == "1y":
            self.model_time = "--model_time_delta 1y"
            return self.model_time
        elif model_time == "ytd":
            self.model_time = "--model_time_delta ytd"
            return self.model_time
        else:
            return ""

    def get_process_factor_value(self):
        logger.info(f"Process Factor Value {self.process_factor.active}")
        if self.process_factor.active:
            return "--price_processing_model high_low"
        else:
            return ""

    def get_weights_value(self):
        weights = self.weights_value.text
        print(f"Weights Value: {weights}")
        if weights == "":
            return ""
        else:
            if "{" or "}" not in weights:
                weights = weights.replace("{","")
                weights = weights.replace("}","")
                weight_string = "--weights" + "{" + weights + "}"
            else:
                weight_string = weights

            return weight_string

    def get_number_to_sim_value(self):
        pass

    def get_number_trials_value(self):
        pass

    def get_sim_date_value(self):
        pass

    def get_seed_value(self):
        pass

    def get_sim_model_value(self):
        pass

    def get_jump_param_value(self):
        pass

    def get_processes_value(self):
        pass

    def get_include_research_value(self):
        pass

    def get_data_source_value(self):
        pass

    def get_default_data_value(self):
        pass

    def get_min_price_value(self):
        pass

    def get_max_price_value(self):
        pass

    def get_num_research_value(self):
        pass

    def get_output_value(self):
        pass

    def get_email_value(self):
        pass

    def get_same_as_user_value(self):
        pass

    def start_calculation_thread(self, instance):
        # Start a new thread for the calculation
        calculation_thread = threading.Thread(target=self.calculate)
        calculation_thread.start()

    def calculate(self):
        logger.info("Calculate button pressed")
        ticker_value = self.get_ticker_value()
        input_instance = StockInputManager(True)
        parser = ArgsParser()
        args = None
        ticker_list = [ticker.strip() for ticker in ticker_value.split(',')]  # Assuming tickers are comma-separated
        # Set the Report args
        use_dow = self.get_use_dow_value()
        include_list = self.get_include_list_value()
        models = self.get_models_values()
        process_factor = self.get_process_factor_value()
        weights = self.get_weights_value()
        # Set the Simulation Args
        number_to_sim = self.get_number_to_sim_value()
        number_trials = self.get_number_trials_value()
        sim_date = self.get_sim_date_value()
        seed = self.get_seed_value()
        sim_model = self.get_sim_model_value()
        j_param = self.get_jump_param_value()
        processes = self.get_processes_value()
        # Set the Research Args
        include_research = self.get_include_research_value()
        data_source = self.get_data_source_value()
        default_data = self.get_default_data_value()
        min_price = self.get_min_price_value()
        max_price = self.get_max_price_value()
        num_research = self.get_num_research_value()
        # Set the Output Args
        output = self.get_output_value()
        email = self.get_email_value()
        same_as_user = self.get_same_as_user_value()

        if same_as_user:
            email = "" # add functionality to copy username/email here from loginscreen

        # Make the Argument
        if len(ticker_list) >= 1:
            argument = f"--ticker {','.join(ticker_list)} {use_dow} {include_list} \
            {self.index} {models} {self.model_time} {process_factor} {weights} {number_to_sim} \
            {number_trials} {sim_date} {seed} {sim_model} {j_param} {processes} {include_research} \
            {data_source} {default_data} {min_price} {max_price} {num_research} \
            {output} {email} "
        else:
            argument = f" {use_dow} {include_list} \
            {index} {models} {model_time} {process_factor} {weights} {number_to_sim} \
            {number_trials} {sim_date} {seed} {sim_model} {j_param} {processes} {include_research} \
            {data_source} {default_data} {min_price} {max_price} {num_research} \
            {output} {email} "

        #args = parser.parse_args(argument)
        #input_instance.set_args(args)
        logger.info(f"Argument set as: {argument}")
        logger.info(f"Calculations complete for ticker: {','.join(ticker_list)}")
        # Update the UI from the main thread
        Clock.schedule_once(lambda dt: self.calculation_complete(ticker_value))

    def calculation_complete(self, ticker_value):
        print(f"Calculations for {ticker_value} are complete!")
        # Update the UI to reflect that the calculations are complete
