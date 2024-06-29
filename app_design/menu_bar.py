# Python Imports 
import logging

# Kivy Imports 
from kivymd.uix.menu import MDDropdownMenu
from kivymd.toast import toast


# Ensure logging.basicConfig is not called after setting the level for your logger
logger = logging.getLogger(__name__)

class MenuBar:
    def __init__(self, screen_manager):
        self.manager = screen_manager

    def callback_left(self):
        print("left Button clicked!")

    def callback_right(self):
        print("Right button clicked")

    def open_menu(self, item):
        menu_items = [
            {
                "text": "Today's Top Stocks",
                "on_release": lambda x="Today's Top Stocks": self.menu_callback_top_stocks(),
            },
            {
                "text": "Today's Worst Stocks",
                "on_release": lambda x="Today's Worst Stocks": self.menu_callback_worse_stocks(),
            },
            {
                "text": "Recent Finance News",
                "on_release": lambda x="Recent Finance News": self.menu_callback_finance_news(),
            },
        ]
        MDDropdownMenu(caller=item, items=menu_items).open()

    def menu_callback_top_stocks(self):
        print("Top Stocks Selected")
        self.manager.current = "top_stocks"

    def menu_callback_worse_stocks(self):
        print("Worse Stocks Selected.")

    def menu_callback_finance_news(self):
        print("Finance News Selected.")

    def option_selected(self, option):
        # Handle what happens when an option in the dropdown menu is selected
        toast(f"Option selected: {option}")
     
    def back_to_menu(self, instance):
        self.manager.current = 'menu'
        logger.info("Going back to Menu screen.")
