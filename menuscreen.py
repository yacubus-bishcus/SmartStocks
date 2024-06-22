# Kivy Imported Modules
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivymd.uix.screen import MDScreen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.behaviors import ButtonBehavior
# App Imported Modules
from customoptions import BackgroundColorBoxLayout

import logging
# Ensure logging.basicConfig is not called after setting the level for your logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class MenuScreen(MDScreen):
    def __init__(self, **kwargs):
        super(MenuScreen, self).__init__(**kwargs)
        layout = BackgroundColorBoxLayout(orientation='vertical')

        # Title
        layout.add_widget(Label(text="Main Menu", font_size='24sp', size_hint=(1, 0.2)))

        # Create A Report Button
        create_report_button = Button(text="Create A Report", size_hint=(1, 0.2))
        create_report_button.bind(on_press=self.create_report)
        layout.add_widget(create_report_button)

        # Schedule Reports Button
        schedule_reports_button = Button(text="Schedule Reports", size_hint=(1, 0.2))
        schedule_reports_button.bind(on_press=self.schedule_reports)
        layout.add_widget(schedule_reports_button)

        # Compare Stocks Button
        compare_stocks_button = Button(text="Compare Stocks", size_hint=(1, 0.2))
        compare_stocks_button.bind(on_press=self.compare_stocks)
        layout.add_widget(compare_stocks_button)

        # DayTrader Button
        daytrader_button = Button(text="DayTrader", size_hint=(1, 0.2))
        daytrader_button.bind(on_press=self.daytrader)
        layout.add_widget(daytrader_button)

        self.add_widget(layout)

    def create_report(self, instance):
        logger.info("Create A Report option selected")

    def schedule_reports(self, instance):
        logger.info("Schedule Reports option selected")

    def compare_stocks(self, instance):
        self.manager.current = 'compare_stocks'

    def daytrader(self, instance):
        logger.info("DayTrader option selected")
