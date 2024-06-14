from colorama import Fore, Style
import inspect
from StockApp.Models import *

"""
Model Handler Class allows each model whether internal to the program or imported
from the users model class access to the list of MyStock objects, market data df,
risk free rate, time period to look at the models and debugging capabilities.
"""
class Model_Handler:
    def __init__(self, myStock_list=None, market_data=None, risk_free_rate=None, time_delta="1mo", debug=False):
        # Initialize attributes
        self.stock_list = myStock_list
        self.market_data = market_data
        self.risk_free_rate = risk_free_rate
        self.time_delta = time_delta
        self.debug = debug

    def __del__(self):
        pass
    """
    When add_model method is called the model must be program internal. The
    method will return the results from each models execute_model method.
    """
    def add_model(self, model_name):
        if self.debug:
            print("Model_Handler::add_model Adding Model -->", model_name)

        if model_name.lower() == "50":
            return self.get_50_model()
        elif model_name.lower() == "200":
            return self.get_200_model()
        elif model_name.lower() == "capm":
            return self.get_capm_model()
        elif model_name.lower() == "rsi":
            return self.get_rsi_model()
        elif model_name.lower() == "fibonacci":
            return self.get_fibonnaci_model()
        elif model_name.lower() == "stocastic_oscillator":
            return self.get_stochastic_oscillator_model()
        elif model_name.lower() == "macd":
            return self.get_macd_model()
        else:
            print(Fore.RED + "USER ERROR: Model_Handler::add_model model_name not found." + Style.RESET_ALL)
            return None

    def set_models(self, model_instances):
        self.model_instances = model_instances

    def add_all_plotting_models(self):
        self.set_models([self.get_capm_instance, self.get_rsi_instance, self.get_fibonnaci_instance, self.get_stochastic_oscillator_instance, self.get_macd_instance])

    def plot_catcher(self):
        fig, axes = plt.subplots(len(self.model_instances), figsize=(10,6* len(self.model_instances)))
        for i, model_instance in enumerate(self.model_instances):
            ax = axes[i] if len(self.model_instances) > 1 else axes
            model_instance.plot(ax)

        plt.tight_layout()
        return fig 
    ## -----------------------GETTERS Functions-----------------------------##

    def get_50_model(self):
        model = Fifty_Day_Model(self.stock_list, self.debug)
        return model.execute_model()

    def get_200_model(self):
        model = TwoHundred_Day_Model(self.stock_list, self.debug)
        return model.execute_model()

    def get_capm_model(self):
        model = CAPM(self.stock_list, self.market_data, self.risk_free_rate, self.time_delta, self.debug)
        return model.execute_model()

    def get_rsi_model(self):
        model = RSI(stock_list=self.stock_list, debug=self.debug)
        return model.execute_model()

    def get_fibonnaci_model(self):
        model = FIBONACCI(myStock_list=self.stock_list, time_delta=self.time_delta, debug=self.debug)
        return model.execute_model()

    def get_stochastic_oscillator_model(self):
        model = STOCHASTIC_OCSILLATOR(myStock_list=self.stock_list, time_delta=self.time_delta, debug=self.debug)
        return model.execute_model()

    def get_macd_model(self):
        model = MACD(myStock_list=self.stock_list, debug=self.debug)
        return model.execute_model()

    def get_capm_instance(self):
        model = CAPM(self.stock_list, self.market_data, self.risk_free_rate, self.time_delta, self.debug)
        model.execute_model()
        return model

    def get_rsi_instance(self):
        model = RSI(myStock_list=self.stock_list, debug=self.debug)
        model.execute_model()
        return model

    def get_fibonnaci_instance(self):
        model = FIBONACCI(myStock_list=self.stock_list, time_delta=self.time_delta, debug=self.debug)
        model.execute_model()
        return model

    def get_stochastic_oscillator_instance(self):
        model = STOCHASTIC_OCSILLATOR(myStock_list=self.stock_list, time_delta=self.time_delta, debug=self.debug)
        model.execute_model()
        return model

    def get_macd_instance(self):
        model = MACD(myStock_list=self.stock_list, debug=self.debug)
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
