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
from app_design.screens.topstockscreen import TopStockScreen
#from app_design.screens.schedulereportscreen import ScheduleReportScreen
#from app_design.screens.daytraderscreen import DayTraderScreen
from app_design.screens.betascreen import BetaScreen
from app_design.SmartStocksBuilder import SmartStocksBuilder
##################################################################################################
## MAIN CLASS 
##################################################################################################
class SmartStocksApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create and initialize ScreenManager
        self.sm = MDScreenManager(transition=MDFadeSlideTransition())
        # Initialize MenuBar with the ScreenManager
        self.menu_bar = MenuBar(screen_manager=self.sm)

    def build(self):
#################################################################################################
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
        SmartStocksBuilder() 
##################################################################################################
        self.sm.add_widget(Builder.load_file("app_design/kv_files/mainscreen.kv"))
        self.sm.add_widget(TopStockScreen(name="top_stocks"))
        self.sm.add_widget(LoginPage(name='login_page'))
        self.sm.add_widget(MenuScreen(name='menu'))
        self.sm.add_widget(CreateReportScreen(name='create_report'))
        self.sm.add_widget(FutureScreen(name='future'))
        self.sm.add_widget(FutureResultScreen(name='future_result'))
        from app_design.screens.comparestockscreen import CompareStocksScreen, CompareStocksOutputScreen
        self.sm.add_widget(CompareStocksScreen(name='compare_stocks'))
        self.sm.add_widget(LuckyScreen(name='lucky'))
        self.sm.add_widget(LuckyResultScreen(name='lucky_result'))
        self.sm.add_widget(CompareStocksOutputScreen(name='compare_stocks_output'))
        self.sm.add_widget(BetaScreen(name='betascreen'))

        return self.sm
##########################################################################################################
## ON START
##########################################################################################################
    def on_start(self):
        logger.info("fps_monitor_start...")
        self.fps_monitor_start()
        logger.info("fps_monitor_start complete.")
        Clock.schedule_once(self.change_screen, 15) # delay for 15 seconds 

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
        self.sm.current = "login_page"

    def on_stop(self):
        logger.info("Application stopping...")
        # Clean up the InternetResearch instance if needed
        if hasattr(self.sm.get_screen('top_stocks'), 'research'):
            self.sm.get_screen('top_stocks').research.stop_thread()
        super().on_stop()
        
if __name__ =="__main__":
    print("Starting SmartStocksApp.run()")
    SmartStocksApp().run()
    print("Run Complete.")