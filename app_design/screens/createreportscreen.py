# Imported Modules
import threading
import logging
from datetime import datetime
import os 
from dotenv import load_dotenv 

# Kivy Imported Modules
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.properties import StringProperty, ObjectProperty, BooleanProperty
from kivymd.uix.button import MDRaisedButton
from kivy.metrics import dp
from kivy.clock import Clock
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.pickers.datepicker import MDDatePicker

# My Imported Modules
from SmartStocksInputManager import SmartStocksInputManager
from ArgsParser import ArgsParser
from OutputManager import Email 

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
    number_to_sim = ObjectProperty(None)
    num_trials = ObjectProperty(None)
    sim_date = ObjectProperty(None)
    seed = ObjectProperty(None)
    jump_param = ObjectProperty(None)
    processes = ObjectProperty(None)
    include_research = ObjectProperty(None)
    min_price = ObjectProperty(None)
    max_price = ObjectProperty(None)
    num_research = ObjectProperty(None)
    output = ObjectProperty(None)
    email = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(CreateReportScreen, self).__init__(**kwargs)
        self.md_bg_color = self.theme_cls.bg_normal  # Correct assignment
        self.add_back_to_menu_button()
        self.add_calculate_button()
        self.index = ""
        self.the_sim_date = datetime.today().date()
        self.model_time = ""
        self.email_value = False 
    
    def show_date_picker(self, focus):
        if not focus:
            return

        date_dialog = MDDatePicker()
        date_dialog.pos = [
            self.sim_date.center_x - date_dialog.width / 2,
            self.sim_date.y - (date_dialog.height + dp(32)),
        ]
        date_dialog.bind(on_save=self.on_save_date)
        date_dialog.open()

    def on_save_date(self, instance, value, date_range):
        # Handle the selected date
        self.the_sim_date = value
        print(f"Selected date: {self.the_sim_date}")
        # Optionally, update the text field with the selected date
        self.sim_date.text = value.strftime('%m/%d/%Y')

    def init_dropdown_menu_sim_model(self):
        menu_items = [
            {"viewclass": "OneLineListItem", "text": f"Item {i}", "height": dp(56),
             "on_release": lambda x=f"Item {i}": self.menu_callback_sim_model(x)}
            for i in range(5)
        ]

        self.menu_sim_model = MDDropdownMenu(
            caller=self.ids.sim_model_dropdown,
            items=menu_items,
            width_mult=4
        )

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

        self.menu_model_time = MDDropdownMenu(
            caller=self.ids.model_time_dropdown,
            items=menu_items,
            width_mult=4
        )

    def menu_callback_sim_model(self, text_item):
        self.ids.sim_model_dropdown.set_item(text_item)
        self.menu_sim_model.dismiss()

    def menu_callback_model_time(self, text_item):
        self.ids.model_time_dropdown.set_item(text_item)
        self.menu_model_time.dismiss()

    def open_menu_sim_model(self, item):
        menu_items = [
            {"text": "Gaussian", "on_release": lambda x="Gaussian": self.get_sim_model_value(x)},
        ]
        MDDropdownMenu(caller=item, items=menu_items).open()

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
            return "--input Stocks.txt"
        else:
            return ""

    def get_index_value(self, index=""):
        logger.info(f"Index Value {index}")
        if index == "S&P500":
            self.index = "--index ^GSPC"
            return self.index
        elif index == "NASDAQ":
            self.index = "--index ^IXIC"
            return self.index
        elif index == "DOW JONES":
            self.index = "--index ^DJI"
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
            self.model_time = "--model_period 1d"
            return self.model_time
        elif model_time == "5d":
            self.model_time = "--model_period 5d"
            return self.model_time
        elif model_time == "1mo":
            self.model_time = "--model_period 1mo"
            return self.model_time
        elif model_time == "3mo":
            self.model_time = "--model_period 3mo"
            return self.model_time
        elif model_time == "6mo":
            self.model_time = "--model_period 6mo"
            return self.model_time
        elif model_time == "1y":
            self.model_time = "--model_period 1y"
            return self.model_time
        elif model_time == "ytd":
            self.model_time = "--model_period ytd"
            return self.model_time
        else:
            return ""

    def get_process_factor_value(self):
        logger.info(f"Process Factor Value {self.process_factor.active}")
        if self.process_factor.active:
            return "--price_model high_low"
        else:
            return ""

    def get_weights_value(self):
        weights = self.weights_value.text
        logger.info(f"Weights Value: {weights}")
        if weights == "":
            return ""
        else:
            if "{" or "}" not in weights:
                weights = weights.replace("{","")
                weights = weights.replace("}","")
                weight_string = "--weights " + "{" + weights + "}"
            else:
                weight_string = "--weights " + weights

            return weight_string

    def get_number_to_sim_value(self):
        logger.info(f"Number of Stocks to Simulate: {self.number_to_sim.text}")
        if self.number_to_sim.text == "":
            return ""

        else:
            return f"--number_to_highlight {self.number_to_sim.text}"

    def get_number_trials_value(self):
        if self.num_trials.value == 0:
            return ""
        else:
            return f"--simulations {int(self.num_trials.value)}"

    def get_sim_date_value(self):
        today = datetime.today().date()
        days = (self.the_sim_date - today).days
        logger.info(f"Sim Date Value: {days}")
        if days <= 0:
            return ""
        else:
            return f"--sim_time {days}"

    def get_seed_value(self):
        logger.info(f"Seed: {self.seed.text}")
        if self.seed.text == "":
            return ""
        else:
            return f"--seed {self.seed.text}"

    def get_sim_model_value(self):
        return "" # Will include other mathematical models in the future

    def get_jump_param_value(self):
        if self.jump_param.value == 0:
            return ""
        else:
            return f"--jump_parameter {self.jump_param.value}"

    def get_processes_value(self):
        if self.processes.value == 0:
            return ""
        else:
            return f"--proc {self.processes.value}"

    def get_include_research_value(self):
        logger.info(f"Include Research Value {self.include_research.active}")
        if self.include_research.active:
            return "--research"
        else:
            return ""

    def get_min_price_value(self):
        logger.info(f"Min Price: {self.min_price.text}")
        if self.min_price.text == "":
            return ""
        else:
            return f"--min_price {self.min_price.text}"

    def get_max_price_value(self):
        logger.info(f"Max Price: {self.max_price}")
        if self.max_price.text == "":
            return ""
        else:
            return f"--max_price {self.max_price.text}"

    def get_num_research_value(self):
        if self.num_research.value == 0:
            return ""
        else:
            return f"--number_to_research {self.num_research.value}"

    def get_output_value(self):
        logger.info(f"Output: {self.output.text}")
        if self.output.text == "":
            return ""
        else:
            return f"--output {self.output.text}"

    def get_email_value(self):
        logger.info(f"Email: {self.email.text}")
        self.email_value = False 
        if self.email.text != "":
            self.email_value = True 

    def start_calculation_thread(self, instance):
        # Start a new thread for the calculation
        calculation_thread = threading.Thread(target=self.calculate)
        calculation_thread.start()

    def calculate(self):
        logger.info("Calculate button pressed")
        ticker_value = self.get_ticker_value()
        input_instance = SmartStocksInputManager()
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
        min_price = self.get_min_price_value()
        max_price = self.get_max_price_value()
        num_research = self.get_num_research_value()
        # Set the Output Args
        output = self.get_output_value()
        email = self.get_email_value()

        # Make the Argument
        if len(ticker_list) >= 1:
            argument = f"--ticker {','.join(ticker_list)} {use_dow} {include_list} \
            {self.index} {models} {self.model_time} {process_factor} {weights} {number_to_sim} \
            {number_trials} {sim_date} {seed} {sim_model} {j_param} {processes} {include_research} \
            {min_price} {max_price} {num_research} \
            {output} "
        else:
            argument = f" {use_dow} {include_list} \
            {self.index} {models} {self.model_time} {process_factor} {weights} {number_to_sim} \
            {number_trials} {sim_date} {seed} {sim_model} {j_param} {processes} {include_research} \
            {min_price} {max_price} {num_research} \
            {output} "

        #args = parser.parse_args(argument)
        #input_instance.set_args(args)
        logger.info(f"Argument set as: {argument}")
        logger.info(f"Calculations complete for ticker: {','.join(ticker_list)}")
        # Update the UI from the main thread
        Clock.schedule_once(lambda dt: self.calculation_complete(ticker_value))

    def calculation_complete(self, ticker_value):
        print(f"Calculations for {ticker_value} are complete!")
        if self.email_value and self.output.text != "":
            load_dotenv()
            google_api_key = os.getenv('GOOGLE_EMAIL_PASSWORD')
            logger.info(google_api_key)
            email_obj = Email(self.output.text)
            email_obj.email_w_attachment(email_to=self.email.text, 
                                     smtp_username="j.bickus2019@gmail.com", 
                                     smtp_password=google_api_key, 
                                     email_subject="Smart Stocks Report", 
                                     email_body="Please find your Smart Stocks Report Attached.")
