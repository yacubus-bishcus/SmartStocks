# Imported Modules
import matplotlib 
matplotlib.use("module://kivy_garden.matplotlib.backend_kivy")
import pandas as pd
import logging
import matplotlib.pyplot as plt
import traceback
import threading

# Kivy Imported Modules
from kivymd.uix.screen import MDScreen
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.scrollview import MDScrollView  # Import MDScrollView
from kivy_garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg, NavigationToolbar2Kivy
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
from kivy.properties import ObjectProperty
from kivy.metrics import dp

# My Modules 
from Models import RSI, FIBONACCI, STOCHASTIC, MACD
from app_design.plotoptions import PlotOptions

logger = logging.getLogger(__name__)

class CompareStocksOutputScreen(MDScreen):
    stock_label = ObjectProperty(None)
    output_label = ObjectProperty(None) 

    def __init__(self, **kwargs):
        super(CompareStocksOutputScreen, self).__init__(**kwargs)
        self.md_bg_color = self.theme_cls.bg_normal 

    def back_to_compare(self, instance):
        self.manager.current = 'compare_stocks'

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

    def start_calculation_thread(self, instance):
        calculation_thread = threading.Thread(target=self.update_output)
        calculation_thread.start()

    def calculation_complete(self):
        logger.info(f"Compare Stocks Calculations are complete!")
        # Update the UI to reflect that the calculations are complete

    def update_output(self, output_text, recommendations, stocks, market_data, model):
        try:
            stock_info_string = [f"{stock.name} ({stock.symbol})  ${stock.price} ({round(stock.daily_percent, 2)})" for stock in stocks]

            i = 0
            for stock in stocks:
                if stock.daily_percent < 0:
                    text_color = (1,0,0,1)  # Red if negative
                else:
                    text_color = (0,1,0,1)  # Green if positive
                self.stock_label.color = text_color
                self.stock_label.text_color = text_color 
                self.stock_label.bold = True 
                if i > 0:
                    self.stock_label.text = self.stock_label.text + stock_info_string[i]
                else:
                    self.stock_label.text = stock_info_string[i]

                i += 1

            if model == "Index Comparison":
                self.fig, self.ax = plt.subplots(figsize=(20,12))
                df = pd.DataFrame(stock.history['Close'] for stock in stocks)
                df = df.T
                df.columns = [stock.name for stock in stocks]
                df2 = pd.DataFrame(market_data)
                df2['Time'] = df2.index
                df2['Time'] = pd.to_datetime(df2['Time'])
                df2.set_index('Time', inplace=True)
                df2.columns = ['Market Price']
                self.ax.plot(df.index, df.values, label=df.columns)
                self.ax.set_xlabel("Date/Time")
                self.ax.set_ylabel("Price")
                self.ax.legend(loc='upper left')
                self.ax2 = self.ax.twinx()
                self.ax2.plot(df2.index, df2.values, label=df2.columns, color='black', linestyle='--')
                self.ax2.set_ylabel("Index Price")
                self.ax2.legend(loc='upper right')
                title_string = "Stock vs Market Price"
                plt.title(title_string)
                self.fig.autofmt_xdate()
            elif model == "Fibonacci Retracement":
                fibo = FIBONACCI(Stock_list=stocks)
                fibo.execute_model()
                self.fig, self.ax = fibo.plot()
            elif model == "MACD":
                macd = MACD(Stock_list=stocks) # defaults to 1mo for now
                macd.execute_model()
                self.fig, self.ax,  = macd.plot()
            elif model == "RSI":
                rsi = RSI(Stock_list=stocks)
                rsi.execute_model()
                self.fig, self.ax,  = rsi.plot()
            elif model == "Stochastic":
                stoch = STOCHASTIC(Stock_list=stocks)
                stoch.execute_model()
                self.fig, self.ax,  = stoch.plot()

            kivy_widget = FigureCanvasKivyAgg(self.fig)
            self.nav1 = NavigationToolbar2Kivy(kivy_widget)
            
            self.ids.graph_layout.add_widget(self.nav1.actionbar)
            self.ids.graph_layout.add_widget(kivy_widget)

            # Customize the toolbar after it has been added to the layout
            Clock.schedule_once(lambda dt: self.customize_toolbar)

            self.output_label.text = output_text if isinstance(output_text, str) else str(output_text)
            if "underperforming" in self.output_label.text:
                self.output_label.text_color = (1,0,0,1) # set label red if underperforming 
                self.output_label.color = (1,0,0,1)
            else:
                self.output_label.text_color = (0,1,0,1) # set label green if overperforming
                self.output_label.color = (0,1,0,1)
            
            logger.info(f"output_label updated: {self.output_label.text}")

            recommendation_df = pd.DataFrame(recommendations)
            # Update table with recommendation_df 
            self.add_data_table(recommendation_df)

        except Exception as e:
            logger.exception(f"Exception in update_output: {e}")
            traceback.print_exc()
            self.output_label.text = f"An error occurred: {e}"

        Clock.schedule_once(lambda dt: self.calculation_complete())

    def add_data_table(self, df):
        column_data = [("Period", dp(30)), ("Strong Buy", dp(30)), ("Buy", dp(30)), ("Hold", dp(30)), 
                       ("Sell", dp(30)), ("Strong Sell", dp(30))]
        
        row_data = [tuple(row) for row in df.itertuples(index=False)]

        data_table = MDDataTable(
            size_hint=(0.8, None),
            height= dp(500),
            pos_hint={'center_x': 0.5},
            rows_num=len(df),
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

    def customize_toolbar(self):
        self.nav1.actionbar.background_color = get_color_from_hex('#3B3B3B')
        if self.nav1.actionbar.children:
            for item in self.nav1.actionbar.children:
                if hasattr(item, 'children'):
                    for sub_item in item.children:
                        sub_item.color = get_color_from_hex('#FFFFFF')  # Set text/icon color to white