# Kivy Imported Modules
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivymd.uix.screen import MDScreen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.behaviors import ButtonBehavior
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDIconButton
from kivymd.uix.label import MDLabel
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Line, Rectangle
from kivymd.uix.relativelayout import MDRelativeLayout
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.stacklayout import MDStackLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.menu import MDDropdownMenu
from kivy.properties import StringProperty
from kivymd.app import MDApp
# App Imported Modules
from app_design.customoptions import BackgroundColorBoxLayout

import logging
# Ensure logging.basicConfig is not called after setting the level for your logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class MyCard(MDCard):
    text = StringProperty()

    def __init__(self, **kwargs):
        super(MyCard, self).__init__(**kwargs)

    def on_press(self):
        # Assuming MenuScreen is the parent of MyCard
        self.parent.parent.parent.on_card_click(self)

class MenuScreen(MDScreen):
    def __init__(self, **kwargs):
        super(MenuScreen, self).__init__(**kwargs)
        self.ids.box.clear_widgets()
        for text in ("Create A Report", "Compare Stocks", "Futures", "Lucky Stock", "Schedule a Report (Beta Only)", "SmartTrader (Beta Only)"):
            self.ids.box.add_widget(
                MyCard(style='elevated', text=text)
            )

    def on_card_click(self, instance):
        # Example of what you can do when a card is clicked
        if instance.text == "Create A Report":
            self.create_report()
        elif instance.text == "Compare Stocks":
            self.compare_stocks()
        elif instance.text == "Futures":
            self.show_futures()
        elif instance.text == "Lucky Stock":
            self.lucky_stock()
        elif instance.text == "Schedule a Report (Beta Only)":
            self.schedule_reports()
        elif instance.text == "SmartTrader (Beta Only)":
            self.smart_trader()

    def create_report(self):
        logger.info("Create A Report option selected")
        self.manager.current = 'create_report'

    def compare_stocks(self):
        self.manager.current = 'compare_stocks'

    def show_futures(self):
        logger.info("Show Futures selected.")

    def lucky_stock(self):
        logger.info("Lucky Stock selected.")

    def schedule_reports(self):
        logger.info("Schedule Reports option selected")

    def smart_trader(self):
        logger.info("Smart Trader option selected")
