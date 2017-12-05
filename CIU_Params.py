"""
Module for Parameter object to hold parameter information in analysis objects
"""


class Parameters(object):
    """
    Object to hold all parameters used in generation of a CIU_analysis object. Starts with
    nothing initialized and adds parameters over time.
    """

    def __init__(self):
        """
        Initialize an empty parameters object with all params set to None
        """
        # Smoothing and processing parameters
        self.smoothing_method = None
        self.smoothing_window = None
        self.smoothing_iterations = None
        self.cropping_window_values = None
        self.interpolation_bins = None

        # Gaussian fitting and filtering parameters
        self.gaussian_int_threshold = None
        self.gaussian_min_spacing = None
        self.gaussian_width_max = None
        self.gaussian_centroid_bound_filter = None
        self.gaussian_centroid_plot_bounds = None

        # Plotting and saving output parameters
        self.plot_extension = None
        self.save_output_csv = None
        self.output_title = None
        self.plot_x_title = None
        self.plot_y_title = None

    def set_params(self, params_dict):
        """
        Set a series of parameters given a dictionary of (parameter name, value) pairs
        :param params_dict: Dictionary, key=param name, value=param value
        :return: void
        """
        for name, value in params_dict.items():
            try:
                # only set the attribute if it is present in the object - otherwise, raise attribute error
                self.__getattribute__(name)
                self.__setattr__(name, value)
            except AttributeError:
                # no such parameter
                print('No parameter name for param: ' + name)
                continue

    def print_params_to_console(self):
        """
        Method to read all parameters out to the console (alphabetical order)
        :return: void
        """
        for paramkey, value in sorted(self.__dict__.items()):
            print('{}: {}'.format(paramkey, value))


def parse_params_file(params_file):
    """
    Parse a CIU_params.txt file for all parameters. Returns a params_dict that can be used to
    set_params on a Parameters object
    :param params_file: File to parse (.txt), headers = '#'
    :return: params_dict: Dictionary, key=param name, value=param value
    """
    param_dict = {}
    try:
        with open(params_file, 'r') as pfile:
            lines = list(pfile)
            for line in lines:
                # skip headers and blank lines
                if line.startswith('#') or line.startswith('\n'):
                    continue
                splits = line.rstrip('\n').split('=')
                param_dict[splits[0].strip()] = splits[1].strip()
        return param_dict
    except FileNotFoundError:
        print('params file not found!')


# testing
if __name__ == '__main__':
    myparams = Parameters()
    mydict = parse_params_file(r"C:\Users\dpolasky\Desktop\CIU_params.txt")
    myparams.set_params(mydict)
    myparams.print_params_to_console()

