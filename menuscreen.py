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
from kivy.properties import StringProperty
from kivymd.app import MDApp
# App Imported Modules
from customoptions import BackgroundColorBoxLayout

import logging
# Ensure logging.basicConfig is not called after setting the level for your logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class MyCard(MDCard):
    text = StringProperty()

class MenuScreen(MDScreen):
    def __init__(self, **kwargs):
        super(MenuScreen, self).__init__(**kwargs)
        layout = MDGridLayout(cols=3, adaptive_size=True, spacing="12dp", pos_hint={'center_x':0.5, "center_y":0.5})
        layout.md_bg_color = MDApp.get_running_app().theme_cls.primary_color  # Set the background color to t
        for text in ("Create A Report", "Compare Stocks", "Futures", "Lucky Stock", "Schedule A Report (Beta Only)", "SmartTrader (Beta Only)"):
            card = MyCard(style='elevated', text=text)
            card.bind(on_release=self.on_card_click)
            layout.add_widget(card)
        self.add_widget(layout)

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

    def create_report(self, instance):
        logger.info("Create A Report option selected")

    def compare_stocks(self, instance):
        self.manager.current = 'compare_stocks'

    def show_futures(self, instance):
        logger.info("Show Futures selected.")

    def lucky_stock(self, instance):
        logger.info("Lucky Stock selected.")

    def schedule_reports(self, instance):
        logger.info("Schedule Reports option selected")

    def smart_trader(self, instance):
        logger.info("Smart Trader option selected")
