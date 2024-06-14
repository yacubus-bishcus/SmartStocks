#from MyStock import Stock
from colorama import Fore, Style
from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

class CompareStocks:
    def __init__(self, stock1=None, stock2=None, debug=None, output=None):
        # Constructor with 4 arguments
        if stock1 is not None and stock2 is not None and debug is not None and output is not None:
            self.stock1 = stock1
            self.stock2 = stock2
            self.output = output
            self.debug = debug
        # Constructor with 3 arguments
        elif stock1 is not None and stock2 is not None and debug is not None:
            self.stock1 = stock1
            self.stock2 = stock2
            self.debug = debug
        # Constructor with 2 arguments defaults debug to false (minimum)
        else:
            self.stock1 = stock1
            self.stock2 = stock2
            self.debug = False

        #Initialize variables
        self.difference = 0


    def compare_daily_stocks(self):
        if self.stock1.daily_percent and self.stock2.daily_percent:
            self.difference = round(self.stock1.daily_percent - self.stock2.daily_percent, 2)

    def compare_50_day_stocks(self):
        if(self.debug):
            print(self.stock1.info)
        if self.stock1.fifty_percent and self.stock2.fifty_percent:
            self.difference = round(self.stock1.fifty_percent - self.stock2.fifty_percent, 2)
        else:
            print("DATA ERROR: compare_50_day_stocks")


    def compare_200_day_stocks(self):
        if self.stock1.twohundred_percent and self.stock2.twohundred_percent:
            self.difference = round(self.stock1.twohundred_percent - self.stock2.twohundred_percent, 2)

    def print_difference(self):
        if self.difference > 0:
            print(self.stock1.name, " is outperforming ", self.stock2.name, " by ", Fore.GREEN + str(self.difference) + Style.RESET_ALL, " percent.")
        else:
            print(self.stock1.name, " is underperforming ", self.stock2.name, " by ", Fore.RED + str(self.difference) + Style.RESET_ALL, " percent.")

    def output_stock_name(self, days=0):
        output_string = str(self.stock1.name)
        self.output.write(output_string, font_size=20, bold=True, alignment=WD_PARAGRAPH_ALIGNMENT.CENTER)
        if days > 0:
            days_string = "In the last " + str(days) + " days: "
            self.output.write(days_string)

    def output_stock_current_price(self):
        output_string = str(self.stock1.name) + " Current Price is: " + str(self.stock1.price)
        self.output.write(output_string)

    def output_difference(self):
        if self.difference > 0:
            #output_string = self.stock1.name+ " is outperforming "+ self.stock2.name, " by " + Fore.GREEN + str(self.difference) + Style.RESET_ALL + " percent."
            output_string = self.stock1.name + " is outperforming " + self.stock2.name + " by " + str(self.difference) + " percent."
            self.output.write(output_string, color=(0,128,0))
        else:
            #output_string = self.stock1.name + " is underperforming " + self.stock2.name+ " by "+ Fore.RED + str(self.difference) + Style.RESET_ALL + " percent."
            output_string = self.stock1.name + " is underperforming " + self.stock2.name + " by " + str(self.difference) + " percent."
            self.output.write(output_string, color=(128,0,0))
