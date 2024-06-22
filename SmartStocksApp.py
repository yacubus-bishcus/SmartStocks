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

    # def on_label_initialized(self):
    #     Logger.warning("MDLabel complete.")
    #
    # def on_floatlayout_initialized(self):
    #     Logger.warning("MDFloatLayout complete.")
    #
    # def on_textbutton_initialized(self):
    #     Logger.warning("MDTextButton complete.")
    #
    # def on_textbutton1_initialized(self):
    #     Logger.warning("MDTextButton1 complete.")
