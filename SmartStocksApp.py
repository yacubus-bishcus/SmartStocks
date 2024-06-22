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
from kivy.clock import Clock

from kivy.app import App
from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivymd.uix.screen import MDScreen
# MyApp Classes
from loginscreen import LoginScreen
from menuscreen import MenuScreen
from comparestockscreen import CompareStocksScreen, CompareStocksOutputScreen



class SmartStocksApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Orange"
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.theme_style_switch_animation = True
        self.theme_cls.theme_style_switch_animation_duration = 0.8
        sm = ScreenManager(transition=FadeTransition())
        #sm = MDScreen(transition=FadeTransition()) # choose transition from NoTransition, SlideTransition, CardTransition, SwapTransition, FadeTransition, WipeTransition, FallOutTransition, RiseInTransition
        sm.add_widget(LoginScreen(name='Smart Stocks'))
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(CompareStocksScreen(name='compare_stocks'))
        sm.add_widget(CompareStocksOutputScreen(name='compare_stocks_output'))

        return sm

    def on_start(self):
        def on_start(*args):
            self.root.md_bg_color = self.theme_cls.backgroundColor

        Clock.schedule_once(on_start)


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
