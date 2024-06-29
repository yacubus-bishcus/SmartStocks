# Imported Modules 
import logging
import threading 

# Kivy Imported Modules 
from kivymd.uix.screen import MDScreen
from kivymd.uix.menu import MDDropdownMenu
from kivy.metrics import dp
from kivy.properties import ObjectProperty
from kivymd.uix.button import MDRaisedButton
from kivy.clock import Clock

# My Imported Modules
from SmartStocksInputManager import SmartStocksInputManager
from ArgsParser import ArgsParser

# Ensure logging.basicConfig is not called after setting the level for your logger
logger = logging.getLogger(__name__)

class FutureScreen(MDScreen):
    ticker_input = ObjectProperty(None)
    num_trials = ObjectProperty(None)
    sim_time = ObjectProperty(None)
    log_returns = ObjectProperty(None)
    include_history = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = self.theme_cls.bg_normal 
        self.add_back_to_menu_button()
        self.add_calculate_button()
        self._index = ""

    @property 
    def index(self):
        return self._index 


    def init_dropdown_menu_index(self):
        menu_items = [
            {"viewclass": "OneLineListItem", "text": f"Item {i}", "height": dp(56),
             "on_release": lambda x=f"Item {i}": self.menu_callback_index(x)}
            for i in range(5)
        ]

        self.menu_sim_model = MDDropdownMenu(
            caller=self.ids.index_dropdown,
            items=menu_items,
            width_mult=4
        )

    def menu_callback_index(self, text_item):
        self.ids.index_dropdown.set_item(text_item)
        self.menu_sim_model.dismiss()

    def open_menu_index(self, item):
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
        
        # Add the menu button to the main layout 
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
    
    @index.setter 
    def index(self, index):
        logger.info(f"Index Value {index}")
        if index == "S&P500":
            self._index = "--index s&p"
        elif index == "NASDAQ":
            self._index = "--index nas"
        elif index == "DOW JONES":
            self._index = "--index dow"
        else:
            self._index = ""

        
    def get_number_trials_value(self):
        return f"--simulations {int(self.num_trials.value)}"
        
    def get_days_to_sim_value(self):
        return f"--simulations {int(self.sim_time.value)}"
    
    def get_use_log_value(self):
        logger.info(f"Use Log Returns Value {self.log_returns.active}")
        if self.log_returns.active:
            return "--use_log_returns"
        else:
            return ""
        
    def get_include_history_value(self):
        logger.info(f"Include History Value {self.include_history.active}")
        if self.include_history.active:
            return "--include_history"
        else:
            return ""

    def start_calculation_thread(self, instance):
        # Start a new thread for the calculation
        calculation_thread = threading.Thread(target=self.calculate)
        calculation_thread.start()
    
    def calculate(self):
        logger.info("Calculate button pressed")
        ticker_value = self.ticker_input.text 
        input_instance = SmartStocksInputManager()
        parser = ArgsParser()
        args = None
        ticker_list = [ticker.strip() for ticker in ticker_value.split(',')]  # Assuming tickers are comma-separated
        # Set the Futures args
        number_trials = self.get_number_trials_value()
        days_to_sim = self.get_days_to_sim_value()
        log_value = self.get_use_log_value() 
        include_history = self.get_include_history_value() 

        # Make the Argument 
        if 1 <= len(ticker_list) <= 5:
            argument = f"--ticker {','.join(ticker_list)} {number_trials} {days_to_sim} \
                {log_value} {include_history}" 
        
        Clock.schedule_once(self.change_screen)

    def change_screen(self, dt):
        self.manager.current = 'future_result'
