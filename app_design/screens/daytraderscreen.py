import logging
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton
from kivy.uix.anchorlayout import AnchorLayout

logger = logging.getLogger(__name__)

class DayTraderScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = self.theme_cls.bg_normal 
        self.add_back_to_menu_button()

    def back_to_menu(self, instance):
        self.manager.current = "menu"

    def add_back_to_menu_button(self):
        anchor_layout = AnchorLayout(anchor_x='right', anchor_y='bottom')
        back_to_menu_button = MDRaisedButton(
            text="Back to Menu",
            size_hint=(None, None),
            size=(200, 50),
            on_release=self.back_to_menu
        )
        anchor_layout.add_widget(back_to_menu_button)
        self.add_widget(anchor_layout)