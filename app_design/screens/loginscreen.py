# Kivy Imported Modules
from kivymd.uix.screen import MDScreen
from kivy.network.urlrequest import UrlRequest

import logging
# Ensure logging.basicConfig is not called after setting the level for your logger
logger = logging.getLogger(__name__)

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
        logger.info("Login successful!")
        self.manager.get_screen('profile').username = self.ids.username_input.text
        # Navigate to next screen or perform desired action

    def on_failure(self, req, result):
        # Handle failed login
        logger.warning("Login failed. Invalid username or password.")
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
    