from colorama import Fore, Style
import inspect
from Models import *
import logging
from collections import namedtuple

# My Modules 
from Futures import Futures
from Models import *

logger = logging.getLogger(__name__)

"""
Model Handler Class allows each model whether internal to the program or imported
from the users model class access to the list of Stock objects, market data df,
risk free rate, to look at the models and debugging capabilities.
"""
class Model_Handler:
    def __init__(self, Stock_list=None, market_data=None, risk_free_rate=None, args=None):
        # Initialize attributes
        self.stock_list = Stock_list
        self.market_data = market_data
        self.risk_free_rate = risk_free_rate
        self.args = args

        self.futures_data = []
        self.sim_market_data = []
        self.sim_market_stock = None

    def __del__(self):
        pass
    """
    When add_model method is called the model must be program internal. The
    method will return the results from each models execute_model method.
    """
    def add_model(self, model_name):
        #logger.info(f"Adding Model --> {model_name}")

        if model_name.lower() == "fifty day":
            return self.get_50_model()
        elif model_name.lower() == "two hundred day":
            return self.get_200_model()
        elif model_name.lower() == "capm":
            return self.get_capm_model()
        elif model_name.lower() == "rsi":
            return self.get_rsi_model()
        elif model_name.lower() == "fibo":
            return self.get_fibonnaci_model()
        elif model_name.lower() == "stochastic":
            return self.get_stochastic_oscillator_model()
        elif model_name.lower() == "macd":
            return self.get_macd_model()
        else:
            logger.error(Fore.RED + "USER ERROR: Model_Handler::add_model model_name not found." + Style.RESET_ALL)
            return None

    def set_models(self, model_instances):
        self.model_instances = model_instances

    # only plot future prices, macd with future prices and rsi
    # to add more requires additional debugging with datetime objects causing
    # issues
    def add_all_plotting_models(self, futures):
        if futures:
            self.set_models([self.get_futures_instance, self.get_macd_instance, self.get_rsi_instance])
        else:
            self.set_models([self.get_macd_instance, self.get_rsi_instance])

    """
    Function 'catches' all model instances and plots each of the calcuations.
    Those plots are tossed to a list and return alongside their plot captions
    """
    def plot_catcher(self, output_filename):
        # Plot = namedtuple('Plot',['title', 'image_path'])
        plt.ioff()
        #fig, axes = plt.subplots(len(self.model_instances), figsize=(10,6* len(self.model_instances)))
        figures = []
        for i, model_instance in enumerate(self.model_instances):
            #ax = axes[i] if len(self.model_instances) > 1 else axes
            plot_obj = model_instance()  # Assuming model_instance is callable and returns a plot object
            figure = plot_obj.plot(stock_name=self.stock_list.symbol)
            caption = plot_obj.get_caption()
            figure.text(0.5,-0.2, caption, ha='center', fontsize=8)
            figure.tight_layout(pad=2.0)
            figures.append(figure)

        return figures

    ## -----------------------GETTERS Functions-----------------------------##

    def get_50_model(self):
        model = Fifty_Day_Model(self.stock_list)
        return model.execute_model()

    def get_200_model(self):
        model = TwoHundred_Day_Model(self.stock_list)
        return model.execute_model()

    def pass_futures_data(self, futures_data):
        self.futures_data = futures_data

    def pass_futures_market_data(self, market_data):
        self.sim_market_data = market_data

    def pass_market_stock(self, stock):
        self.sim_market_stock = stock

    def get_capm_model(self):
        model = CAPM(Stock_list=self.stock_list, md=self.market_data, rfr=self.risk_free_rate)
        return model.execute_model()

    def get_rsi_model(self):
        model = RSI(Stock_list=self.stock_list)
        return model.execute_model()

    def get_fibonnaci_model(self):
        model = FIBONACCI(Stock_list=self.stock_list)
        return model.execute_model()

    def get_stochastic_oscillator_model(self):
        model = STOCHASTIC(Stock_list=self.stock_list)
        return model.execute_model()

    def get_macd_model(self):
        model = MACD(Stock_list=self.stock_list)
        return model.execute_model()

    def get_futures_instance(self):
        model = Futures(self.futures_data, self.sim_market_data, self.args)
        model.execute_model()
        return model

    def get_capm_instance(self):
        if self.futures_data is not None:
            model = CAPM(Stock_list=self.stock_list, md=self.market_data, rfr=self.risk_free_rate, futures_data=self.futures_data.iloc[:,0])
        else:
            model = CAPM(Stock_list=self.stock_list, md=self.market_data, rfr=self.risk_free_rate)
        model.execute_model()
        return model

    def get_rsi_instance(self):
        if self.futures_data is not None:
            model = RSI(Stock_list=self.stock_list, futures_data=self.futures_data.iloc[:,0])
        else:
            model = RSI(Stock_list=self.stock_list)
        model.execute_model()
        return model

    def get_fibonnaci_instance(self):
        model = FIBONACCI(Stock_list=self.stock_list, futures_data=self.futures_data)
        model.execute_model()
        return model

    def get_stochastic_oscillator_instance(self):
        model = STOCHASTIC(Stock_list=self.stock_list, futures_data=self.futures_data)
        model.execute_model()
        return model

    def get_macd_instance(self):
        if self.futures_data is not None:
            model = MACD(Stock_list=self.stock_list, futures_data=self.futures_data.iloc[:,0])
        else:
            model = MACD(Stock_list=self.stock_list)
        model.execute_model()
        return model
    """
    The import_model method is crucial to importing user defined models. When
    importing a model the import_model method will look for the module name and
    class name and return the imported model class
    """
    def import_model(self, module_name, class_name):
        """
        Import a class from a specified module.

        Args:
            module_name (str): Name of the module from which to import the class.
            class_name (str): Name of the class to import.

        Returns:
            class: The imported class object.

        Raises:
            ImportError: If the module or class cannot be imported.
            AttributeError: If the specified class cannot be found in the module.
        """
        try:
            # Import the module dynamically
            module = __import__(module_name, fromlist=[class_name])
            # Get the class from the module using getattr
            imported_class = getattr(module, class_name)
            return imported_class
        except ImportError:
            raise ImportError(f"Failed to import module '{module_name}'")
        except AttributeError:
            raise AttributeError(f"Class '{class_name}' not found in module '{module_name}'")

    def requires_inputs(self, func):
        """
        Check if a function requires inputs.

        Args:
            func (function): The function to check.

        Returns:
            bool: True if the function requires inputs, False otherwise.
        """
        # Get the signature of the function
        signature = inspect.signature(func)

        # Check if the signature has parameters
        if signature.parameters:
            return True
        else:
            return False
