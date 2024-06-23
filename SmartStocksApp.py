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

# Kivy Imported Modules
import kivy
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.transition import MDFadeSlideTransition
from kivy.lang import Builder
from kivymd.uix.menu import MDDropdownMenu
# MyApp Classes
from loginscreen import LoginScreen, LoginPage
from menuscreen import MenuScreen
# from comparestockscreen import CompareStocksScreen, CompareStocksOutputScreen


class SmartStocksApp(MDApp):
    def build(self):
        self.theme_cls.theme_style_switch_animation = True
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Orange"
        Builder.load_file('loginkv.kv')  # Load the KV file
        logger.info("loginkv.kv loaded.")
        Builder.load_file('menukv.kv')
        logger.info("menukv.kv loaded.")
        sm = MDScreenManager(transition=MDFadeSlideTransition())
        logger.info("Screen Manager Initialized.")
        sm.add_widget(LoginPage(name='login_page'))
        logger.info("LoginPage Initialized.")
        #sm.add_widget(LoginScreen(name='Smart Stocks'))
        sm.add_widget(MenuScreen(name='menu'))
        logger.info("MenuScreen Initialized.")
        from comparestockscreen import CompareStocksScreen, CompareStocksOutputScreen
        sm.add_widget(CompareStocksScreen(name='compare_stocks'))
        logger.info("CompareStocksScreen Initialized.")
        sm.add_widget(CompareStocksOutputScreen(name='compare_stocks_output'))
        logger.info("CompareStocksOutputScreen Initialized.")
        return sm

    def on_start(self):
        logger.info("fps_monitor_start...")
        self.fps_monitor_start()
        logger.info("fps_monitor_start complete.")

    def switch_theme_style(self, *args):
        self.theme_cls.primary_palette = (
            "Orange" if self.theme_cls.primary_palette == "Red" else "Red"
        )
        self.theme_cls.theme_style = (
            "Dark" if self.theme_cls.theme_style == "Light" else "Light"
        )
        self.root.get_ids().label.text = (
            "Theme style - {}".format(self.theme_cls.theme_style)
        )

    def callback_left(self):
        print("left Button clicked!")

    def callback_right(self):
        print("Right button clicked")

    def open_menu(self, item):
        menu_items = [
            {
                "text": "Today's Top Stocks",
                "on_release": lambda x="Today's Top Stocks": self.menu_callback_top_stocks(),
            },
            {
                "text": "Today's Worst Stocks",
                "on_release": lambda x="Today's Worst Stocks": self.menu_callback_worse_stocks(),
            },
            {
                "text": "Recent Finance News",
                "on_release": lambda x="Recent Finance News": self.menu_callback_finance_news(),
            },
        ]
        MDDropdownMenu(caller=item, items=menu_items).open()

    def menu_callback_top_stocks(self):
        print("Top Stocks Selected")

    def menu_callback_worse_stocks(self):
        print("Worse Stocks Selected.")

    def menu_callback_finance_news(self):
        print("Finance News Selected.")

    def option_selected(self, option):
        # Handle what happens when an option in the dropdown menu is selected
        toast(f"Option selected: {option}")
