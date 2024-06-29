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
        print("Profile button clicked")
        self.manager.current = "profile"

    def open_menu(self, item):
        menu_items = [
            {
                "text": "Today's Top Stocks",
                "on_release": lambda x="Today's Top Stocks": self.menu_callback_top_stocks(),
            },
            {
                "text": "Feedback",
                "on_release": lambda x="Feedback": self.menu_callback_feedback(),
            },
            {
                "text": "About",
                "on_release": lambda x="About": self.menu_callback_about(),
            },
        ]
        MDDropdownMenu(caller=item, items=menu_items).open()

    def menu_callback_top_stocks(self):
        print("Top Stocks Selected")
        self.manager.current = "top_stocks"

    def menu_callback_about(self):
        print("About Selected.")
        self.manager.current = "about"

    def menu_callback_feedback(self):
        print("Feedback Selected.")
        self.manager.current ="feedback"

    def option_selected(self, option):
        # Handle what happens when an option in the dropdown menu is selected
        toast(f"Option selected: {option}")
     
    def back_to_menu(self, instance):
        self.manager.current = 'menu'
        logger.info("Going back to Menu screen.")
