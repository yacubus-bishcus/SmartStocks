# Kivy Imported Modules
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivy.properties import StringProperty
import logging
# Ensure logging.basicConfig is not called after setting the level for your logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class MyCard(MDCard):
    text = StringProperty()

    def __init__(self, **kwargs):
        super(MyCard, self).__init__(**kwargs)

    def on_press(self):
        # Assuming MenuScreen is the parent of MyCard
        self.parent.parent.parent.on_card_click(self)

class MenuScreen(MDScreen):
    def __init__(self, **kwargs):
        super(MenuScreen, self).__init__(**kwargs)
        self.ids.box.clear_widgets()
        for text in ("Create A Report", "Compare Stocks", "Futures", "Lucky Stock", "Schedule a Report (Beta Only)", "SmartTrader (Beta Only)"):
            self.ids.box.add_widget(
                MyCard(style='elevated', text=text)
            )

    def on_card_click(self, instance):
        # Example of what you can do when a card is clicked
        if instance.text == "Create A Report":
            self.create_report()
        elif instance.text == "Compare Stocks":
            self.compare_stocks()
        elif instance.text == "Futures":
            self.show_futures()
        elif instance.text == "Lucky Stock":
            self.lucky_stock()
        elif instance.text == "Schedule a Report (Beta Only)":
            self.schedule_reports()
        elif instance.text == "SmartTrader (Beta Only)":
            self.smart_trader()

    def create_report(self):
        logger.info("Create A Report option selected")
        self.manager.current = 'create_report'

    def compare_stocks(self):
        self.manager.current = 'compare_stocks'

    def show_futures(self):
        logger.info("Show Futures selected.")
        self.manager.current = "future"

    def lucky_stock(self):
        logger.info("Lucky Stock selected.")
        self.manager.current = "lucky"

    def schedule_reports(self):
        logger.info("Schedule Reports option selected")

    def smart_trader(self):
        logger.info("Smart Trader option selected")
