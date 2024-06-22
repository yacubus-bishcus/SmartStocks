# Kivy Imported Modules
from kivy.app import App
from kivy.uix.widget import Widget
from kivymd.uix.label import MDLabel
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivymd.uix.screen import MDScreen
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.graphics import Color, Line
from kivy.lang import Builder

# App Imported Modules
from customoptions import BackgroundColorBoxLayout


import logging
# Ensure logging.basicConfig is not called after setting the level for your logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class LoginPage(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def verify_credentials(self, username, password):
        # Replace with actual backend API URL or database query
        api_url = "http://your-backend-api-url/login"
        params = {"username": username, "password": password}

        # Example using UrlRequest, replace with appropriate network request library
        req = UrlRequest(api_url, on_success=self.on_success, on_failure=self.on_failure, req_body=params)

    def on_success(self, req, result):
        # Handle successful login
        print("Login successful!")
        # Navigate to next screen or perform desired action

    def on_failure(self, req, result):
        # Handle failed login
        print("Login failed. Invalid username or password.")
        # Provide feedback to the user, e.g., show an error message

    def on_login_button_press(self):
        username = self.ids.username_input.text
        password = self.ids.password_input.text
        self.verify_credentials(username, password)

    def login(self, instance):
        # For simplicity, let's just navigate to the menu screen on any login attempt
        self.manager.current = 'menu'

    def create_account(self, instance):
        logger.info("Create Account option selected")
        # Navigate to a create account screen or handle account creation

    def forgot_password(self, instance):
        logger.info("Forget Password option selected.")
        
class LoginScreen(MDScreen):
    def __init__(self, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        layout = BackgroundColorBoxLayout(orientation='vertical')
        app = App.get_running_app()  # Get the current running app instance
        # Title layout with white outline
        title_layout = MDBoxLayout(orientation='horizontal', size_hint=(1, 0.1), md_bg_color=app.theme_cls.primary_color)

        with title_layout.canvas.before:
            Color(1, 1, 1, 1)  # Set the outline color to white
            self.line = Line(width=2)

        # Title label with black color
        title_label = Label(text="Smart Stocks", font_size='48sp', size_hint=(1, 0.4), color=(0, 0, 0, 1))
        title_layout.add_widget(title_label)

        layout.add_widget(title_layout)
        title_layout.bind(size=self.update_line, pos=self.update_line)

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

    def update_line(self, instance, value):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(1, 1, 1, 1)  # Set the outline color to white
            Line(rectangle=(instance.x, instance.y, instance.width, instance.height), width=2)

    def login(self, instance):
        # For simplicity, let's just navigate to the menu screen on any login attempt
        self.manager.current = 'menu'

    def create_account(self, instance):
        logger.info("Create Account option selected")
        # Navigate to a create account screen or handle account creation
