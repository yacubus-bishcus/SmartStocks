# Python Imported Modules 
import logging
import threading
import traceback

# Kivy Imported Modules 
from kivymd.uix.screen import MDScreen
from kivy_garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg, NavigationToolbar2Kivy
from kivy.clock import Clock
from kivy.properties import ObjectProperty

# My Modules 
from app_design.plotoptions import PlotOptions

# Ensure logging.basicConfig is not called after setting the level for your logger
logger = logging.getLogger(__name__)

class FutureResultScreen(MDScreen):
    output_label = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = self.theme_cls.bg_normal 

    def clear_plots(self):
        self.ids.graph_layout.clear_widgets()

    def zoom_in(self, *args):
        plot_obj = PlotOptions(self.ax, self.ids.graph_layout)
        plot_obj.zoom_in(*args)

    def zoom_out(self, *args):
        plot_obj = PlotOptions(self.ax, self.ids.graph_layout)
        plot_obj.zoom_out(*args)

    def pan_left(self, *args):
        plot_obj = PlotOptions(self.ax, self.ids.graph_layout)
        plot_obj.pan_left(*args)

    def pan_right(self, *args):
        plot_obj = PlotOptions(self.ax, self.ids.graph_layout)
        plot_obj.pan_right(*args)

    def reset_view(self, *args):
        plot_obj = PlotOptions(self.ax, self.ids.graph_layout)
        plot_obj.reset_view(*args) 

    def back_to_menu(self):
        self.manager.current = "future"

    def start_calculation_thread(self, instance):
        calculation_thread = threading.Thread(target=self.update_output)
        calculation_thread.start()

    def calculation_complete(self):
        logger.info(f"Compare Stocks Calculations are complete!")
        # Update the UI to reflect that the calculations are complete

    def update_output(self, results, args):
        try:
            model, filtered_prices = results 
            result = model.plot(stock_name="Stocks", current_prices=filtered_prices, show_every_nth_errorbar=args.show_every_nth_errorbar)
            self.fig = result 
            self.ax = self.fig.axes[0]
            caption = model.caption 
            if self.fig is not None:
                self.fig.text(0.5,-0.2, caption, ha='center', fontsize=8)
                self.fig.tight_layout(pad=2.0)

            kivy_widget = FigureCanvasKivyAgg(self.fig) 
            self.nav1 = NavigationToolbar2Kivy(kivy_widget) 
            self.ids.graph_layout.add_widget(self.nav1.actionbar) 
            self.ids.graph_layout.add_widget(kivy_widget)

        except Exception as e: 
            logger.exception(f"Exception in update_output: {e}")
            traceback.print_exc() 
            self.output_label.text = f"An Error Occured: {e}"

        Clock.schedule_once(lambda dt: self.calculation_complete()) 
