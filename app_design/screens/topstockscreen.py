import logging

# Kivy Imported Modules
from kivymd.uix.screen import MDScreen
from kivy.metrics import dp
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.label import MDLabel 
from kivy.clock import Clock

# My Modules
from SmartStocksResearch import InternetResearch

# Ensure logging.basicConfig is not called after setting the level for your logger
logger = logging.getLogger(__name__)

class TopStockScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.research = InternetResearch()
        Clock.schedule_once(self.on_start, 1)  # Schedule the addition of the data table after the screen is initialized

    def on_start(self, *args):
        self.add_back_to_menu_button()
        Clock.schedule_once(self.start_data_thread, 1)

    def back_to_menu(self, instance):
        self.manager.current = "menu"

    def add_back_to_menu_button(self):
        back_to_menu_button = MDRaisedButton(
            text="Back to Menu",
            size_hint=(None, None),
            size=(200, 50),
            pos_hint={"right": 1, "bottom": 1},
            on_release=self.back_to_menu
        )
        self.ids.main_layout.add_widget(back_to_menu_button)

    def start_data_thread(self, instance):
        # Start a new thread for the data
        self.research.start_get_top_gainers_thread(self.update_data_table)

    def update_data_table(self, top_stocks):
        Clock.schedule_once(lambda dt: self._update_data_table(top_stocks), 0)

    def _update_data_table(self, top_stocks):
        table = MDDataTable(
            size_hint=(0.9, 0.6),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            column_data=[
                ("Symbol", dp(30)),
                ("Name", dp(30)),
                ("Price", dp(30)),
                ("Change", dp(30)),
                ("% Change", dp(30)),
                ("Volume", dp(30))
            ],
            row_data=[
                (
                    stock['symbol'],
                    stock['name'],
                    stock['price'],
                    stock['change'],
                    stock['percent_change'],
                    stock['volume']
                ) for stock in top_stocks
            ]
        )
        self.ids.main_layout.add_widget(table)
        logger.info("Top Stocks Data Table Added!")
