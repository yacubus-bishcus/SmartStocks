# Python Imported Modules 
import matplotlib.pyplot as plt
import logging
import threading
import traceback
from colorama import Fore, Style 

# Kivy Imported Modules 
from kivymd.uix.screen import MDScreen
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.scrollview import MDScrollView  # Import MDScrollView
from kivy.metrics import dp
from kivy_garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg, NavigationToolbar2Kivy
from kivy.clock import Clock
from kivy.properties import ObjectProperty

#My Modules 
from app_design.plotoptions import PlotOptions

# Ensure logging.basicConfig is not called after setting the level for your logger
logger = logging.getLogger(__name__)

class LuckyResultScreen(MDScreen):
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

    def back_to_lucky(self):
        self.manager.current = "lucky"

    def start_calculation_thread(self, instance):
        calculation_thread = threading.Thread(target=self.update_output)
        calculation_thread.start()

    def calculation_complete(self):
        logger.info(f"Compare Stocks Calculations are complete!")
        # Update the UI to reflect that the calculations are complete

    def update_output(self, results):
        try:
            perf_df, mse, r_squared = results
            if not perf_df.empty and mse != 0: 
                logger.debug(perf_df.head(10)) 
                self.fig, self.ax = plt.subplots(figsize=(20,12))
                self.ax.bar(perf_df["Symbol"], perf_df["SAM"])
                self.ax.set_xlabel("Stock Ticker")
                self.ax.set_ylabel("SAM")
                plt.title("Research Stocks SAM")

                kivy_widget = FigureCanvasKivyAgg(self.fig) 
                self.nav1 = NavigationToolbar2Kivy(kivy_widget)
                self.ids.graph_layout.add_widget(self.nav1.actionbar) 
                self.ids.graph_layout.add_widget(kivy_widget)
                self.output_label.text = f"Data Set MSE: {round(mse,3)} Data Set R-Squared {round(r_squared,3)}"
                logger.info(f"Output Label Updated: {self.output_label.text}")
                
                # Update table with perf_df
                self.add_data_table(perf_df)
            else: 
                self.output_label.text = "Check your filters returned empty dataset. Price Cut maybe too high for researched number."
                logger.warning(Fore.YELLOW + "Printing Performance Dataframe..." + Style.RESET_ALL)
                logger.info(perf_df)

        except Exception as e: 
            logger.exception(f"Exception in update_output: {e}")
            traceback.print_exc() 
            self.output_label.text = f"An Error Occured: {e}"

        Clock.schedule_once(lambda dt: self.calculation_complete())

    def add_data_table(self, perf_df):
        column_data = [("Symbol", dp(30)), ("50 Day", dp(30)), ("200 Day", dp(30)), ("CAPM", dp(30)), 
                       ("MACD", dp(30)), ("RSI", dp(30)), ("Stochastic", dp(30)), ("WAM", dp(30)), 
                       ("SAM", dp(30)), ("Price", dp(30))]
        
        row_data = [tuple(row) for row in perf_df.itertuples(index=False)]

        data_table = MDDataTable(
            size_hint=(0.8, None),
            height= dp(500),
            pos_hint={'center_x': 0.5},
            rows_num=len(perf_df),
            column_data=column_data,
            row_data=row_data,
            padding=dp(10),
            use_pagination=True
        )
        
        self.ids.table_layout.clear_widgets()  # Clear any existing widgets in table_layout

        scroll_view = MDScrollView(size_hint=(1, None), height=dp(300))
        scroll_view.add_widget(data_table)
        self.ids.table_layout.add_widget(scroll_view)  # Add scroll_view to table_layout instead of data_table
        logger.info("Data table added to the layout")