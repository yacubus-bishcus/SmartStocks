from colorama import Fore, Style
import inspect
#from Models import *

class Model_Handler:
    def __init__(self, stock_list=None, market_data=None, risk_free_rate=None, time_delta="1mo", debug=False):
        # Initialize attributes
        self.stock_list = stock_list
        self.market_data = market_data
        self.risk_free_rate = risk_free_rate
        self.time_delta = time_delta
        self.debug = debug

    def __del__(self):
        pass

    def add_model(self, model_name):
        if self.debug:
            print("Model_Handler::add_model Adding Model -->", model_name)

        if model_name.lower() == "default":
            return self.get_default_model()
        elif model_name.lower() == "capm":
            return self.get_capm_model()
        elif model_name.lower() == "rsi":
            return self.get_rsi_model()
        else:
            print(Fore.RED + "USER ERROR: Model_Handler::add_model model_name not found." + Style.RESET_ALL)
            return None

    ## -----------------------GETTERS Functions-----------------------------##

    def get_default_model(self):
        model = Simple_Model(self.stock_list, self.debug)
        return model.execute_model()

    def get_capm_model(self):
        model = CAPM(self.stock_list, self.market_data, self.risk_free_rate, self.time_delta, self.debug)
        return model.execute_model()

    def get_rsi_model(self):
        model = RSI(stock_list=self.stock_list, debug=self.debug)
        return model.execute_model()

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
