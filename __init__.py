"""

__init__.py files can be empty or be used to initialize
__init__.py needs to be in each subpackage
EXAMPLE USAGE
Import module1 from the main package
import my_package.module1
import StockApp.StockOutputManager

Import module2 from subpackage1
import my_package.subpackage1.module2
import StockApp.stock_analysis.StockResearch

"""
from . import StockOutputManager
from StockApp.input_handler_package.StockInputManager import StockInputManager
from StockApp.input_handler_package.StockInput import StockInput
from StockApp.model_package import *
#from StockApp.stock_analysis import *
