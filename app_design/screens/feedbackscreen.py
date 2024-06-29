# Imported Modules 
import logging

# Kivy Imported Modules 
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton

# Ensure logging.basicConfig is not called after setting the level for your logger
logger = logging.getLogger(__name__)

class FeedbackScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = self.theme_cls.bg_normal 
        self.add_back_to_menu_button()

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