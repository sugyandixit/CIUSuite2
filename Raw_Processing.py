"""
Methods for raw data pre-processing (smoothing, interpolation, etc) for CIU-type data
Author: Dan Polasky
Date: 10/6/2017
"""

import numpy as np
import scipy.signal
import scipy.interpolate
from CIU_raw import CIURaw
from CIU_analysis_obj import CIUAnalysisObj


def get_data(fname):
    """
    Read _raw.csv file and generate a CIURaw object containing its raw data and filename
    :param fname: string - path to _raw.csv file to read
    :return: CIURaw object with rawdata, axes, and filename initialized
    """
    rawdata = np.genfromtxt(fname, missing_values=[""], filling_values=[0], delimiter=",")
    row_axis = rawdata[1:, 0]
    col_axis = rawdata[0, 1:]
    raw_obj = CIURaw(rawdata[1:, 1:], row_axis, col_axis, fname)
    return raw_obj


# Generate lists of trap collision energies and drift times used for the plots ###
def get_axes(rawdata):
    row_axis = rawdata[1:, 0]
    col_axis = rawdata[0, 1:]
    return row_axis, col_axis


def normalize_by_col(raw_data_matrix):
    """
    Generate a normalized dataset where each column has been normalized to 1 individually. Returns
    normalized 2D matrix only.
    :param raw_data_matrix: CIURaw.rawdata - 2D numpy array with no axes
    :return: Normalized 2D numpy array of raw data
    """
    maxint = np.amax(raw_data_matrix, axis=0)  # find the maximum value for each energy
    if 0 in maxint:
        # set any columns with 0 total intensity to have normalized intensity of 0 as well
        norm = raw_data_matrix / maxint

        index_tup = np.where(maxint == 0)
        index_list = index_tup[0]
        for index in index_list:
            # zero the column at this index (where the max value is 0 - replace all NANs with 0s)
            norm[:, index] = np.zeros(np.shape(norm[:, index]))
    else:
        # no zero values, so simply divide
        norm = raw_data_matrix / maxint
    return norm


def sav_gol_smooth(ciu_data_matrix, smooth_window):
    """
    Apply savitsky-golay smoothing to each column (CV) of the 2D matrix supplied
    :param ciu_data_matrix: input matrix (2D, columns (axis 1) gets smoothed) - supply without axes
    :param smooth_window: Savitsky golay smoothing window to apply
    :return: smoothed data (same size/format as input)
    """
    # ensure window length is odd
    if smooth_window % 2 == 0:
        smooth_window += 1

    # swap axes to access the columns
    cv_data = np.swapaxes(ciu_data_matrix, 0, 1)
    output_data = np.ndarray(np.shape(cv_data))

    # smooth each column and return the data (axes swapped back to normal)
    index = 0
    while index < len(cv_data):
        smoothed_col = scipy.signal.savgol_filter(cv_data[index], smooth_window, 2)
        output_data[index] = smoothed_col
        index += 1
    output_data = np.swapaxes(output_data, 0, 1)

    return output_data


def find_nearest(array, value):
    """
    Get the index in the array nearest to the input value. Handles values outside the
    array by returning the end value in the correct direction.
    :param array: array-like object to search within
    :param value: value to find nearest index in the array
    :return: index (int) of closest match in the array
    """
    idx = (np.abs(array - value)).argmin()
    return idx


def crop(analysis_obj, crop_vals):
    """
    Crops the data and axes arrays to the nearest values specified in the crop vals list.
    If provided crop values are outside the axes, will crop to the nearest value.
    :param analysis_obj: CIUAnalysisObj with data to crop
    :param crop_vals: list of values to crop to in form [cv_low, cv_high, dt_low, dt_high]
    :return: New CIUAnalysisObj with cropped data and new axes
    """
    # Determine the indices corresponding to the values nearest to those entered by the user
    dt_axis = analysis_obj.axes[0]
    cv_axis = analysis_obj.axes[1]
    dt_low = find_nearest(dt_axis, crop_vals[0])
    dt_high = find_nearest(dt_axis, crop_vals[1])
    cv_low = find_nearest(cv_axis, crop_vals[2])
    cv_high = find_nearest(cv_axis, crop_vals[3])

    # allow single axis cropping - ignore one axis if its provided values are equal
    crop_dt = True
    crop_cv = True
    if dt_high == dt_low:
        crop_dt = False
    if cv_low == cv_high:
        crop_cv = False

    # crop the data and axes
    ciu_data_matrix = analysis_obj.ciu_data
    if crop_dt:
        ciu_data_matrix = ciu_data_matrix[dt_low:dt_high + 1]  # crop the rows
        dt_axis = dt_axis[dt_low:dt_high + 1]
    ciu_data_matrix = np.swapaxes(ciu_data_matrix, 0, 1)
    if crop_cv:
        ciu_data_matrix = ciu_data_matrix[cv_low:cv_high + 1]  # crop the columns
        cv_axis = cv_axis[cv_low:cv_high + 1]
    ciu_data_matrix = np.swapaxes(ciu_data_matrix, 0, 1)
    new_axes = [dt_axis, cv_axis]

    # crop_obj = CIUAnalysisObj(analysis_obj.raw_obj, ciu_data_matrix, new_axes,
    #                           analysis_obj.gauss_params)
    # crop_obj.params = analysis_obj.params
    # crop_obj.raw_obj_list = analysis_obj.raw_obj_list
    # save output to the analysis object
    analysis_obj.ciu_data = ciu_data_matrix
    analysis_obj.axes = new_axes
    return analysis_obj


def interpolate_cv(norm_data, axes, num_bins=200):
    """
    interpolate along the collision voltage (x) axis to allow for unevenly spaced data collection
    :param norm_data: input data (with axes still present) to interpolate
    :param axes: axes list to use for interpolation (x-axis, y-axis)
    :param num_bins: number of bins to have after interpolate (default 200)
    :return: interpolated data matrix with x-axis, but not y-axis???
    """
    # get starting and ending cv values
    xaxis = axes[0]
    start_cv = xaxis[0]
    end_cv = xaxis[len(xaxis) - 1]
    new_cv_axis = np.linspace(start_cv, end_cv, num_bins)
    newaxes = [new_cv_axis, axes[1]]

    interpolated_data = []

    for ycolumn in norm_data[:, :]:
        interp_func = scipy.interpolate.interp1d(xaxis, ycolumn)
        new_intensities = interp_func(new_cv_axis)
        interpolated_data.append(new_intensities)

    return interpolated_data, newaxes


def average_ciu(list_of_data_matrices):
    """
    Average CIU fingerprints and return the averaged and standard deviation matrices (SD only
    if n >= 3).
    :param list_of_data_matrices: List of CIU data matrices (2D numpy array with no axes label info)
    :return: averaged_matrix, std_dev_matrix as 2D numpy arrays of same shape as input
    """
    avg_matrix = np.mean(list_of_data_matrices, axis=0)
    std_matrix = np.std(list_of_data_matrices, axis=0)

    return avg_matrix, std_matrix


