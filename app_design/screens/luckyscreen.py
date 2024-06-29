# Imported Modules 
import logging
import threading 

# Kivy Imported Modules 
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton
from kivy.clock import Clock

# Ensure logging.basicConfig is not called after setting the level for your logger
logger = logging.getLogger(__name__)

class LuckyScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = self.theme_cls.bg_normal 
        self.add_back_to_menu_button()
        self.add_calculate_button()
        
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

    def start_calculation_thread(self, instance):
        # Start a new thread for the calculation
        calculation_thread = threading.Thread(target=self.calculate)
        calculation_thread.start()

    def calculate(self):
        logger.info("Calculate button pressed")

        Clock.schedule_once(self.change_screen)

    def change_screen(self, dt):
        self.manager.current = 'lucky_result'