# Imported Modules 
import logging
import threading 

# Kivy Imported Modules 
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton
from kivy.properties import ObjectProperty
from kivy.clock import Clock

# My Imported Modules
from SmartStocksInputManager import SmartStocksInputManager
from ArgsParser import ArgsParser
from SmartStocksResearch import Research

# Ensure logging.basicConfig is not called after setting the level for your logger
logger = logging.getLogger(__name__)

class LuckyScreen(MDScreen):
    clear_plots_switch = ObjectProperty(None)
    num_research = ObjectProperty(None)
    num_highlight = ObjectProperty(None)
    min_price = ObjectProperty(None)
    max_price = ObjectProperty(None)
    calculation_label = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = self.theme_cls.bg_normal
        self.add_calculate_button()
        
    def back_to_menu(self):
        self.manager.current = "menu"

    def on_clear_plots_switch_active(self):
        if self.clear_plots_switch.active:
            logger.info("Switch is ON - Clear Plots")
            self.manager.get_screen('lucky_result').clear_plots()

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

    def start_calculation_thread(self, instance):
        # Start a new thread for the calculation
        calculation_thread = threading.Thread(target=self.calculate)
        calculation_thread.start()

    def calculate(self):
        logger.info("Calculate button pressed")
        Clock.schedule_once(self.show_calculation_label)
        input_instance = SmartStocksInputManager() 
        parser = ArgsParser() 
        if self.min_price.text == "":
            min_price = "1.00"
        else:
            min_price = self.min_price.text 

        if self.max_price.text == "":
            max_price = "1000.00"
        else:
            max_price = self.max_price.text 

        args = parser.parse_args(f"--research --number_to_research {int(self.num_research.value)} --number_to_highlight {int(self.num_highlight.value)} --min_price {min_price} --max_price {max_price}")
        output = None 
        if parser.conduct_smartstock_input_checks():
            research = Research(number_to_research=args.number_to_research)
            input_instance.tickers = (None, None, None, research)
            input_instance.stocks = (input_instance.tickers)
            results = input_instance.apply_input_conditions(output=output, args=args) #this is a dataframe with the top performers 
            
            output_screen = self.manager.get_screen('lucky_result')
            Clock.schedule_once(lambda dt: output_screen.update_output(results=results))
            Clock.schedule_once(lambda dt: self.hide_calculation_label())
            Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'lucky_result'))
        else:
            self.calculation_label.text = "User Input Error. See Documentation."
            self.show_calculation_label() 

    def show_calculation_label(self, *args):
        self.calculation_label.opacity = 1

    def hide_calculation_label(self, *args):
        self.calculation_label.opacity = 0