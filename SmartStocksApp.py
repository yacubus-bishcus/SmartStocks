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
################################################################################################
# Kivy Imported Modules
################################################################################################
from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.transition import MDFadeSlideTransition
from kivy.lang import Builder
from kivy.clock import Clock
#################################################################################################
## MyApp Classes
#################################################################################################
from app_design.screens.loginscreen import LoginPage
from app_design.screens.menuscreen import MenuScreen
from app_design.screens.createreportscreen import CreateReportScreen
from app_design.screens.futurescreen import FutureScreen 
from app_design.screens.futureresultscreen import FutureResultScreen 
from app_design.screens.luckyscreen import LuckyScreen
from app_design.screens.luckyresultscreen import LuckyResultScreen 
from app_design.menu_bar import MenuBar
from app_design.screens.schedulereportscreen import ScheduleReportScreen
from app_design.screens.daytraderscreen import DayTraderScreen
from app_design.screens.betascreen import BetaScreen
##################################################################################################
## MAIN CLASS 
##################################################################################################
class SmartStocksApp(MDApp, MenuBar):
    global sm
    sm = MDScreenManager(transition=MDFadeSlideTransition())
    def build(self):
        super().__init__()
#################################################################################################
        Builder.load_file('app_design/kv_files/login.kv') 
        logger.info("login.kv loaded.")
        Builder.load_file('app_design/kv_files/menu.kv')
        logger.info("menu.kv loaded.")
        Builder.load_file('app_design/kv_files/createreportscreen.kv')
        logger.info("createreportscreen.kv loaded.")
        Builder.load_file('app_design/kv_files/future.kv')
        logger.info('future.kv loaded.')
        Builder.load_file('app_design/kv_files/futureresultscreen.kv')
        logger.info("futureresultscreen kv loaded.")
        Builder.load_file('app_design/kv_files/luckyscreen.kv')
        logger.info("luckyscreen kv loaded.")
        Builder.load_file("app_design/kv_files/luckyresultscreen.kv")
        logger.info("luckyresultscreen loaded.")
        Builder.load_file("app_design/kv_files/daytraderscreen.kv")
        logger.info("daytraderscreen.kv loaded.")
        Builder.load_file("app_design/kv_files/schedulereportscreen.kv")
        logger.info("schedulereportscreen loaded.")
        Builder.load_file("app_design/kv_files/betascreen.kv")
        logger.info("betascreen.kv loaded")
##################################################################################################
        self.theme_cls.theme_style_switch_animation = True
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Orange"
        self.theme_cls.primary_hue = "500"
        self.secondary_color_dark = self.theme_cls.primary_palette 
        primary_color = self.theme_cls.primary_color
        secondary_color = [0.68, 0.85, 0.90, 1]  # Light blue color
        # Lighten the primary color
        self.primary_color_light = [min(1, c + 0.2) for c in primary_color[:3]] + [primary_color[3]]
        self.color_light_text = [0, 0, 0, 1]  # Dark text for light background
        self.secondary_color_light = [min(1, c + 0.2) for c in secondary_color[:3]] + [secondary_color[3]]
        # Darken the primary color
        self.primary_color_dark = [max(0, c - 0.2) for c in primary_color[:3]] + [primary_color[3]]
        self.color_dark_text = [1, 1, 1, 1]  # Light text for dark background
        self.secondary_color_dark = [max(0, c - 0.2) for c in secondary_color[:3]] + [secondary_color[3]]
        self.title = "SMART STOCKS"
##################################################################################################        
        sm.add_widget(Builder.load_file("app_design/kv_files/mainscreen.kv"))
        sm.add_widget(LoginPage(name='login_page'))
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(CreateReportScreen(name='create_report'))
        sm.add_widget(FutureScreen(name='future'))
        sm.add_widget(FutureResultScreen(name='future_result'))
        from app_design.screens.comparestockscreen import CompareStocksScreen, CompareStocksOutputScreen
        sm.add_widget(CompareStocksScreen(name='compare_stocks'))
        sm.add_widget(LuckyScreen(name='lucky'))
        sm.add_widget(LuckyResultScreen(name='lucky_result'))
        sm.add_widget(CompareStocksOutputScreen(name='compare_stocks_output'))
        sm.add_widget(BetaScreen(name='betascreen'))
        

        return sm
##########################################################################################################
## ON START
##########################################################################################################
    def on_start(self):
        logger.info("fps_monitor_start...")
        self.fps_monitor_start()
        logger.info("fps_monitor_start complete.")
        Clock.schedule_once(self.change_screen, 10) # delay for 10 seconds 

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
    
    def change_screen(self, dt):
        sm.current = "login_page"

if __name__ =="__main__":
    print("Starting SmartStocksApp.run()")
    SmartStocksApp().run()
    print("Run Complete.")