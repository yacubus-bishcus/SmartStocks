from kivymd.uix.screen import MDScreen
from kivy.clock import Clock

class BetaScreen(MDScreen):
    def on_enter(self, *args):
        # Schedule the screen change after 10 seconds
        Clock.schedule_once(self.change_screen, 2)

    def change_screen(self, dt):
        self.manager.current = "menu"