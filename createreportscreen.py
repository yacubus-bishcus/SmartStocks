# Kivy Imported Modules
from kivymd.uix.screen import MDScreen
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.properties import StringProperty, ObjectProperty
from kivymd.uix.button import MDRaisedButton
from kivy.base import runTouchApp
from kivy.app import App

class CheckItem(MDBoxLayout):
    text = StringProperty()
    group = StringProperty()

class CreateReportScreen(MDScreen):
    ticker_input = ObjectProperty(None)  # Add a reference to the ticker input
    def __init__(self, **kwargs):
        super(CreateReportScreen, self).__init__(**kwargs)
        self.md_bg_color = self.theme_cls.bg_normal  # Correct assignment
        self.add_back_to_menu_button()
        self.add_calculate_button()

    def back_to_menu(self, instance):
        self.manager.current = "menu"

    def get_ticker_value(self):
        ticker_value = self.ticker_input.text
        print(f"Ticker Value: {ticker_value}")  # Print the ticker value for debugging
        return ticker_value

    def add_back_to_menu_button(self):
        back_to_menu_button = MDRaisedButton(
            text="Back to Menu",
            size_hint=(None, None),
            size=(200,50),
            pos_hint= {"center_x":0.5},
            on_release=self.back_to_menu
        )
        self.ids.main_layout.add_widget(back_to_menu_button)

    def add_calculate_button(self):
        # Create a new button
        calculate_button = MDRaisedButton(
            text="Calculate",
            size_hint=(None, None),
            size=(200, 50),
            pos_hint={"center_x": 0.5},
            on_release=self.calculate
        )

        # Add the button to the main layout
        self.ids.main_layout.add_widget(calculate_button)

    def calculate(self, instance):
        print("Calculate button pressed")
        # Add your calculation logic here
