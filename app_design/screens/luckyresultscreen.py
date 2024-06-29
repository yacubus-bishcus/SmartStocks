# Python Imported Modules 
import matplotlib.pyplot as plt
import numpy as np
import logging

# Kivy Imported Modules 
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivy_garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg

# Ensure logging.basicConfig is not called after setting the level for your logger
logger = logging.getLogger(__name__)

class LuckyResultScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = self.theme_cls.bg_normal 
        self.add_back_to_menu_button()
        
    def on_kv_post(self, base_widget):
        self.build_ui()
        self.plot_graph()

    def build_ui(self):
        main_layout = self.ids.main_layout
        #self.graph_layout = MDBoxLayout(size_hint_y=0.7)  # Adjust size_hint_y to 0.7
        self.graph_layout = MDBoxLayout(size_hint_y=None, height='300dp')
        main_layout.add_widget(self.graph_layout)

        button_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height='56dp', padding='10dp', spacing='10dp')

        zoom_in_button = MDRaisedButton(text='Zoom In', on_press=self.zoom_in)
        zoom_out_button = MDRaisedButton(text='Zoom Out', on_press=self.zoom_out)
        pan_left_button = MDRaisedButton(text='Pan Left', on_press=self.pan_left)
        pan_right_button = MDRaisedButton(text='Pan Right', on_press=self.pan_right)
        reset_button = MDRaisedButton(text='Reset', on_press=self.reset_view)

        button_layout.add_widget(zoom_in_button)
        button_layout.add_widget(zoom_out_button)
        button_layout.add_widget(pan_left_button)
        button_layout.add_widget(pan_right_button)
        button_layout.add_widget(reset_button)

        main_layout.add_widget(button_layout)

    def plot_graph(self):
        # Create a Matplotlib figure
        self.fig, self.ax = plt.subplots()  # store ax as an instance variable
        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        self.ax.plot(x, y)
        self.ax.set_title('Sine Wave')
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')

        # Add the figure to the Kivy widget
        self.graph_layout.clear_widgets()
        self.graph_layout.add_widget(FigureCanvasKivyAgg(self.fig))

    def zoom_in(self, *args):
        logger.info("Zoom In Button Pressed!")
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        self.ax.set_xlim(xlim[0] * 0.8, xlim[1] * 0.8)
        self.ax.set_ylim(ylim[0] * 0.8, ylim[1] * 0.8)
        self.graph_layout.children[0].figure.canvas.draw()

    def zoom_out(self, *args):
        logger.info("Zoom Out Button Pressed!")
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        self.ax.set_xlim(xlim[0] / 0.8, xlim[1] / 0.8)
        self.ax.set_ylim(ylim[0] / 0.8, ylim[1] / 0.8)
        self.graph_layout.children[0].figure.canvas.draw()

    def pan_left(self, *args):
        logger.info("Pan Left Button Pressed!")
        xlim = self.ax.get_xlim()
        self.ax.set_xlim(xlim[0] - 1, xlim[1] - 1)
        self.graph_layout.children[0].figure.canvas.draw()

    def pan_right(self, *args):
        logger.info("Pan Right Button Pressed!")
        xlim = self.ax.get_xlim()
        self.ax.set_xlim(xlim[0] + 1, xlim[1] + 1)
        self.graph_layout.children[0].figure.canvas.draw()

    def reset_view(self, *args):
        logger.info("Reset Button Pressed!")
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(-1, 1)
        self.graph_layout.children[0].figure.canvas.draw()

    def back_to_menu(self, instance):
        self.manager.current = "lucky"

    def add_back_to_menu_button(self):
        back_to_menu_button = MDRaisedButton(
            text="Back to Lucky Input",
            size_hint=(None, None),
            size=(200,50),
            pos_hint= {"center_x":0.5},
            on_release=self.back_to_menu
        )
        self.ids.main_layout.add_widget(back_to_menu_button)