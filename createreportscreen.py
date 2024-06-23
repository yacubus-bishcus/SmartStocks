# Imported Modules
import threading
import logging

# Kivy Imported Modules
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.properties import StringProperty, ObjectProperty, ListProperty
from kivymd.uix.button import MDRaisedButton
from kivy.base import runTouchApp
from kivy.app import App
from kivy.clock import Clock

# My Imported Modules
from InputManager import StockInputManager
from ArgsParser import ArgsParser

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class CheckItem(MDBoxLayout):
    text = StringProperty()
    group = StringProperty()

class CreateReportScreen(MDScreen):
    ticker_input = ObjectProperty(None)  # Add a reference to the ticker input
    def __init__(self, **kwargs):
        super(CreateReportScreen, self).__init__(**kwargs)
        self.md_bg_color = self.theme_cls.bg_normal  # Correct assignment
        self.add_back_to_menu_button()
        self.add_calculate_button()

    def back_to_menu(self, instance):
        self.manager.current = "menu"

    def get_ticker_value(self):
        ticker_value = self.ticker_input.text
        print(f"Ticker Value: {ticker_value}")  # Print the ticker value for debugging
        return ticker_value

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

    def get_use_dow_value(self):
        pass

    def get_include_list_value(self):
        pass

    def get_index_value(self):
        pass

    def get_models_values(self):
        pass

    def get_model_time_value(self):
        pass

    def get_process_factor_value(self):
        pass

    def get_weights_value(self):
        pass

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
        index = self.get_index_value()
        models = self.get_models_values()
        model_time = self.get_model_time_value()
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
            {index} {models} {model_time} {process_factor} {weights} {number_to_sim} \
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
