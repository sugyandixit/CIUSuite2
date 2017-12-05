"""
Main entry point for CIUSuite 2. Designed to allow the user to choose files and perform
processing to generate analysis objects, and process analysis objects. Probably will need
a (very) basic GUI of some kind.
"""

# GUI test
import tkinter as tk
import pygubu
from tkinter import messagebox
from tkinter import filedialog
import matplotlib.pyplot as plt
import os
import Raw_Processing
import Gaussian_Fitting
from CIU_analysis_obj import CIUAnalysisObj
import pickle
import CIU_Params


hard_file_path_ui = r"C:\Users\dpolasky\Desktop\CIUSuite2.ui"
hard_params_file = r"C:\Users\dpolasky\Desktop\CIU_params.txt"


class CIUSuite2(object):
    """

    """
    def __init__(self, master_window):
        """

        :param master_window:
        """
        # create a Pygubu builder
        self.builder = builder = pygubu.Builder()

        # load the UI file
        builder.add_from_file(hard_file_path_ui)
        # create widget using provided root (Tk) window
        self.mainwindow = builder.get_object('CIU_app_top', master_window)

        callbacks = {
            'on_button_rawfile_clicked': self.on_button_rawfile_clicked
        }
        builder.connect_callbacks(callbacks)

        # load parameter file
        self.params_obj = CIU_Params.parse_params_file(hard_params_file)
        params_text = self.builder.get_object('Text_params')
        params_text.delete(1.0, tk.END)
        params_text.insert(tk.INSERT, 'Parameters loaded from hard file')

    def on_button_rawfile_clicked(self):
        """
        Open a filechooser for the user to select raw files, then process them
        :return:
        """
        raw_files = open_files([('_raw.csv', '_raw.csv')])
        filestring = '\n'.join([os.path.basename(x).rstrip('_raw.csv') for x in raw_files])
        # clear any existing text, then write the list of files to the display
        self.builder.get_object('Text_analysis_list').delete(1.0, tk.END)
        self.builder.get_object('Text_analysis_list').insert(tk.INSERT, filestring)


# ****** CIU Main I/O methods ******
def open_files(filetype):
    """
    Open a tkinter filedialog to choose files of the specified type
    :param filetype: filetype filter in form [(name, extension)]
    :return: list of selected files
    """
    files = filedialog.askopenfilenames(filetype=filetype)
    return files


def write_ciu_csv(save_path, ciu_data, axes=None):
    """
    Method to write an _raw.csv file for CIU data. If 'axes' is provided, assumes that the ciu_data
    array does NOT contain axes and if 'axes' is None, assumes ciu_data contains axes.
    :param save_path: Full path to save location (SHOULD end in _raw.csv)
    :param ciu_data: 2D numpy array containing CIU data in standard format (rows = DT bins, cols = CV)
    :param axes: (optional) axes labels, provided as (row axis, col axis). if provided, assumes the data array does not contain axes labels.
    :return: void
    """
    with open(save_path, 'w') as outfile:
        if axes is not None:
            # write axes first if they're provided
            args = ['{}'.format(x) for x in axes[1]]    # get the cv-axis now to write to the header
            line = ','.join(args)
            line = ',' + line
            outfile.write(line + '\n')

            index = 0
            for row in ciu_data:
                # insert the axis label at the start of each row
                args = ['{}'.format(x) for x in row]
                args.insert(0, str(axes[0][index]))
                index += 1
                line = ','.join(args)
                outfile.write(line + '\n')
        else:
            # axes are included, so just write everything to file with comma separation
            args = ['{}'.format(x) for x in ciu_data]
            line = ','.join(args)
            outfile.write(line + '\n')


def ciu_plot(data, axes, output_dir, plot_title, x_title, y_title, extension):
    """
    Generate a CIU plot in the provided directory
    :param data: 2D numpy array with rows = DT, columns = CV
    :param axes: axis labels (list of [DT-labels, CV-labels]
    :param output_dir: directory in which to save the plot
    :param plot_title: filename and plot title, INCLUDING file extension (e.g. .png, .pdf, etc)
    :param x_title: x-axis title
    :param y_title: y-axis title
    :param extension: file extension for plotting, default png. Must be image format (.png, .pdf, .jpeg, etc)
    :return: void
    """
    plt.clf()
    output_path = os.path.join(output_dir, plot_title + extension)
    plt.title(plot_title)
    plt.contourf(axes[1], axes[0], data, 100, cmap='jet')  # plot the data
    plt.xlabel(x_title)
    plt.ylabel(y_title)
    plt.colorbar(ticks=[0, .25, .5, .75, 1])  # plot a colorbar
    plt.savefig(output_path)
    plt.close()


def generate_raw_obj(raw_file):
    """
    Open an _raw.csv file and read its data into a CIURaw object to return
    :param raw_file: (string) filename of the _raw.csv file to read
    :return: CIURaw object with raw data, filename, and axes
    """
    raw_obj = Raw_Processing.get_data(raw_file)
    return raw_obj


def process_raw_obj(raw_obj, params_obj):
    """
    Run all initial raw processing stages (data import, smoothing, interpolation, cropping)
    on a raw file using the parameters provided in a Parameters object. Returns a new
    analysis object with the processed data
    :param raw_obj: the CIURaw object containing the raw data to process
    :param params_obj: Parameters object containing processing parameters
    :return: CIUAnalysisObj with processed data
    """
    # normalize, smooth, and crop data (if requested)
    norm_data = Raw_Processing.normalize_by_col(raw_obj.rawdata)

    # interpolate data
    axes = (raw_obj.dt_axis, raw_obj.cv_axis)
    if params_obj.interpolation_bins > 0:
        norm_data, axes = Raw_Processing.interpolate_cv(norm_data, axes, params_obj.interpolation_bins)

    if params_obj.smoothing_window is not None:
        i = 0
        while i < params_obj.smoothing_iterations:
            norm_data = Raw_Processing.sav_gol_smooth(norm_data, params_obj.smoothing_window)
            i += 1

    if params_obj.cropping_window_values is not None:  # If no cropping, use the whole matrix
        norm_data, axes = Raw_Processing.crop(norm_data, axes, params_obj.cropping_window_values)

    analysis_obj = CIUAnalysisObj(raw_obj, norm_data, axes)
    analysis_obj.params = params_obj

    return analysis_obj


def run_gaussian_fitting(analysis_obj):
    """
    Perform gaussian fitting on an analysis object. NOTE: object must have initial raw processing
    already performed and a parameters object instantiated. Updates the analysis object.
    :param analysis_obj: CIUAnalysisObj with normalized data and parameters obj already present
    :return: void (updates the analysis_obj)
    """
    params = analysis_obj.params
    Gaussian_Fitting.gaussian_fit_ciu(analysis_obj,
                                      intensity_thr=params.gaussian_int_threshold,
                                      min_spacing=params.gaussian_min_spacing,
                                      filter_width_max=params.gaussian_width_max,
                                      centroid_bounds=params.gaussian_centroid_bound_filter)


def save_gaussian_outputs(analysis_obj, outputpath):
    """
    Write Gaussian output data and diagnostics to file location specified by outputpath
    :param analysis_obj: CIUAnalysisObj with gaussian fitting previously performed
    :param outputpath: directory in which to save output
    :return: void
    """
    analysis_obj.save_gaussfits_pdf(outputpath)
    analysis_obj.plot_centroids(outputpath, analysis_obj.params.gaussian_centroid_plot_bounds)
    analysis_obj.plot_fwhms(outputpath)
    analysis_obj.save_gauss_params(outputpath)


def save_analysis_obj(analysis_obj, outputdir=None):
    """
    Pickle the CIUAnalysisObj for later retrieval
    :param analysis_obj: CIUAnalysisObj to save
    :param outputdir: (optional) directory in which to save. Default = raw file directory
    :return: void
    """
    file_extension = '.ciu'

    if outputdir is not None:
        picklefile = os.path.join(outputdir, analysis_obj.raw_obj.filename.rstrip('_raw.csv') + file_extension)
    else:
        picklefile = os.path.join(os.path.dirname(analysis_obj.raw_obj.filepath),
                                  analysis_obj.raw_obj.filename.rstrip('_raw.csv') + file_extension)

    with open(picklefile, 'wb') as pkfile:
        pickle.dump(analysis_obj, pkfile)


if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()
    ciu_app = CIUSuite2(root)
    root.mainloop()
