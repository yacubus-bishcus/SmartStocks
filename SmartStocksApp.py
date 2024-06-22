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

# MyApp Classes
from loginscreen import LoginScreen
from menuscreen import MenuScreen
from comparestockscreen import CompareStocksScreen, CompareStocksOutputScreen


class SmartStocksApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='Smart Stocks'))
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(CompareStocksScreen(name='compare_stocks'))
        self.compare_screen = CompareStocksOutputScreen(name='compare_stocks_output')
        #self.compare_screen.display_table(data)
        sm.add_widget(self.compare_screen)

        return sm
