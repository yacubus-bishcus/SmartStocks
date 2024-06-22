# Kivy Imported Modules
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image

# App Imported Modules
from customoptions import BackgroundColorBoxLayout


import logging
# Ensure logging.basicConfig is not called after setting the level for your logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        layout = BackgroundColorBoxLayout(orientation='vertical')

        # Title
        layout.add_widget(Label(text="Smart Stocks", font_size='48sp', size_hint=(1, 0.2), color=(0, 0, 0, 1)))

        # Image
        layout.add_widget(Image(source='logo.png', size_hint=(1, 0.3)))

        # Username Input
        username_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.1))
        username_layout.add_widget(Label(text="Username:", size_hint=(0.3, 1), color=(0, 0, 0, 1)))
        self.username_input = TextInput(size_hint=(0.7, 1))
        username_layout.add_widget(self.username_input)
        layout.add_widget(username_layout)

        # Password Input
        password_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.1))
        password_layout.add_widget(Label(text="Password:", size_hint=(0.3, 1), color=(0, 0, 0, 1)))
        self.password_input = TextInput(password=True, size_hint=(0.7, 1))
        password_layout.add_widget(self.password_input)
        layout.add_widget(password_layout)

        # Login Button
        login_button = Button(text="Login", size_hint=(1, 0.1))
        login_button.bind(on_press=self.login)
        layout.add_widget(login_button)

        # Create Account Button
        create_account_button = Button(text="Create Account", size_hint=(1, 0.1))
        create_account_button.bind(on_press=self.create_account)
        layout.add_widget(create_account_button)

        self.add_widget(layout)

    def login(self, instance):
        # For simplicity, let's just navigate to the menu screen on any login attempt
        self.manager.current = 'menu'

    def create_account(self, instance):
        logger.info("Create Account option selected")
        # Navigate to a create account screen or handle account creation
