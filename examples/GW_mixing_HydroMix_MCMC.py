"""
Created on: 18th July 2019 (Harsh Beria)
Last updated on
What it does?

Runs a MCMC implementation of HydroMix to estimate snow ratio in groundwater with the isotopic ratios generated by the script
GW_conceptual.py
The main feature is that this script can use different time periods during the computation of snow ratio

SourceFiles used:
OutputFiles/GW_conceptual/

OutputFiles processed:
Figures made:
"""

from __future__ import division
import numpy as np
import random, datetime, calendar
import pandas as pd
from hydromix.mixingfunctions import *
import matplotlib.pyplot as plt


# Main variables

rain_eff, snow_eff = 0.1, 0.1

# Mixing model parameters
NUMBER_ITERATIONS = 3000
LAMBDA_RANGE = [0., 1.]  # LAMBDA values imply the fraction of snow in groundwater
# Number of best simulations using which lambda is computed
BEST_SIM_PER = 5.  # In percentage

YEARS = 100  # Number of years for which simulation was carried out
LAST_YEARS = 2  # Number of years at the end of the timeseries from which isotopic data is sampled

# Options are "Snowfall/Snowmelt", tells us which isotopic ratio is to be used to find groundwater recharge using HydroMix
which_snow = "Snowmelt"
WEIGHTED = 1  # 0 => non-weighted mixing, 1 => weighted mixing

JUMP_PERCENTAGE = 5  # In percentage (JUMP_PERCENTAGE/2 in both directions)

PATH = "../../../Downloads/Zenodo_dataset/Zenodo_dataset/OutputFiles/GW_conceptual/"
OUTPUTPATH = "OutputFiles/GW_conceptual/Rainfall_" + which_snow + "_mixing_last_" + str(LAST_YEARS) + "Yr"
if (WEIGHTED):
    OUTPUTPATH += "_weighted_MCMC/"
else:
    OUTPUTPATH += "_MCMC/"

#################################################################################################################################
# %% Initializing the seeds
np.random.seed(15544)  # Setting up a common seed number for numpy function
random.seed(55452)  # Setting up random seed for the random function

# %% Mixing for all the proportions of rain and snow efficiency in recharging groundwater

while rain_eff <= 1.:
    snow_eff = 0.1
    while (snow_eff <= 1.):

        filename = PATH + "RAIN_" + str(rain_eff) + "_SNOW_" + str(snow_eff) + ".csv"
        df = pd.read_csv(filename)

        # Computing the proportion of groundwater recharged from snow in long term
        recharge_rain_amount = sum(df["Rain recharge (mm)"].values)
        recharge_snow_amount = sum(df["Snow recharge (mm)"].values)
        actual_snow_ratio_long_term = recharge_snow_amount / (recharge_rain_amount + recharge_snow_amount)

        # Computing the proportion of groundwater recharged from snow in short term (corresponding to the isotopic data period)
        recharge_rain_amount = sum(df["Rain recharge (mm)"].values[(YEARS - LAST_YEARS) * 365:])
        recharge_snow_amount = sum(df["Snow recharge (mm)"].values[(YEARS - LAST_YEARS) * 365:])
        actual_snow_ratio_short_term = recharge_snow_amount / (recharge_rain_amount + recharge_snow_amount)

        # Building list containing isotopic ratio of rain, snowfall and groundwater
        random_rain_iso, random_snow_iso, random_gw_iso = [], [], []
        random_rain_amount, random_snow_amount = [], []  # Amount of rain and snowmelt corresponding to the isotopic ratio
        for year_index in range(YEARS - LAST_YEARS, YEARS):
            for month in range(1, 13):

                # Subsetting the dataframe
                startDayNumb = datetime.datetime(2001, month, 1).timetuple().tm_yday
                start_index = year_index * 365 + startDayNumb
                end_index = start_index + calendar.monthrange(2001, month)[1]

                # Rainfall amount and isotopic ratio
                rain_amount = df["Rainfall (mm)"].values[start_index: end_index + 1]  # Amount of rainfall
                rain_isotopic_ratio = df["Precip isotopic ratio"].values[
                                      start_index: end_index + 1]  # Isotopic ratio of rainfall

                # Amount of snowfall or snowmelt
                if which_snow == "Snowfall":
                    snow_amount = df["Snowfall (mm)"].values[start_index: end_index + 1]  # Amount of snowfall
                    snow_isotopic_ratio = df["Precip isotopic ratio"].values[
                                          start_index: end_index + 1]  # Snowfall isotopic ratio
                elif (which_snow == "Snowmelt"):
                    snow_amount = df["Snowmelt (mm)"].values[start_index: end_index + 1]  # Amount of snowmelt
                    # Shifted up by 1 row because the current snowmelt isotopic ratio is the snowpack isotopic ratio at the last timestep
                    snow_isotopic_ratio = df["Snowpack isotopic ratio"].values[
                                          start_index - 1: end_index]  # Snowmelt isotopic ratio

                storage_isotopic_ratio = df["Storage isotopic ratio"].values[
                                         start_index: end_index + 1]  # Groundwater isotopic ratio

                # Only considering days when it rained or [snowed or the snow melted]
                rain_index = np.nonzero(rain_amount)[0]  # Day when there was rain
                snow_index = np.nonzero(snow_amount)[0]  # Day when there was snowfall or snowmelt

                # Isotopic ratio of rainfall and snowfall/snowmelt
                rain_Iso, snow_Iso = rain_isotopic_ratio[rain_index], snow_isotopic_ratio[snow_index]
                # Magnitude of rainfall and snowfall/snowmelt
                temp_rain_amount, temp_snow_amount = rain_amount[rain_index], snow_amount[snow_index]

                # Choosing values of rain and snowfall/snowmelt isotopic ratio to be used in HydroMix
                if (len(rain_Iso) != 0):
                    #					# Randomly choose one monthly rainfall sample
                    #					random_rain_iso.append(random.sample(rain_Iso, 1)[0])
                    #					random_rain_amount.append(random.sample(temp_rain_amount)[0])

                    # Choose all the rainfall samples
                    random_rain_iso.extend(rain_Iso)
                    random_rain_amount.extend(temp_rain_amount)

                if (len(snow_Iso) != 0):
                    #					# Randomly choose one monthly snowfall/snowmelt sample
                    #					random_snow_iso.append(random.sample(snow_Iso, 1)[0])
                    #					random_snow_amount.append(random.sample(temp_snow_amount, 1)[0])

                    # Choose all the snowfall/snowmelt samples
                    random_snow_iso.extend(snow_Iso)
                    random_snow_amount.extend(temp_snow_amount)

                # Randomly choose one monthly groundwater sample
                random_gw_iso.append(random.sample(storage_isotopic_ratio, 1)[0])

        # Defining weights for rain and snowfall/snowmelt samples
        random_rain_weight = np.array([i * j for i, j in zip(random_rain_iso, random_rain_amount)]) / sum(
            random_rain_amount + random_snow_amount)
        random_snow_weight = np.array([i * j for i, j in zip(random_snow_iso, random_snow_amount)]) / sum(
            random_rain_amount + random_snow_amount)

        # Running the mixing model

        # List of initial parameter values
        initParam = [np.random.uniform(LAMBDA_RANGE[0], LAMBDA_RANGE[1])]

        # Lower and upper limits of the model parameters
        paramLimit = [LAMBDA_RANGE]

        # Standard deviation of H2 in groundwater
        H2_std = np.std(random_gw_iso, ddof=1)

        if (WEIGHTED):  # Running HydroMix taking into account weights
            LOGLIKELIHOOD_H2, PARAM_H2 = hydro_mix_weighted_mcmc(random_snow_iso, random_snow_weight, random_rain_iso,
                                                                 random_rain_weight,
                                                                 random_gw_iso, H2_std, initParam, paramLimit,
                                                                 NUMBER_ITERATIONS, JUMP_PERCENTAGE)
            snowRatioLis_H2 = [i[0] for i in PARAM_H2]
        else:  # Running HydroMix without taking into account weights
            LOGLIKELIHOOD_H2, PARAM_H2 = hydro_mix_mcmc(random_snow_iso, random_rain_iso, random_gw_iso, H2_std,
                                                        initParam,
                                                        paramLimit, NUMBER_ITERATIONS, JUMP_PERCENTAGE)
            snowRatioLis_H2 = [i[0] for i in PARAM_H2]

        # Writing in a csv file
        final_lis = [["Snow ratio", "Log likelihood", "Error std"]]
        path = OUTPUTPATH + "results_RAIN_" + str(rain_eff) + "_SNOW_" + str(snow_eff) + ".csv"
        for index in range(0, len(LOGLIKELIHOOD_H2)):
            final_lis.append([round(snowRatioLis_H2[index], 4), round(LOGLIKELIHOOD_H2[index], 4), round(H2_std, 4)])


        #		# Creating and saving figure
        #		plt.figure(figsize=(10,6))
        #		plt.hist(lambda_h2[0:int(0.01 * best_sim_per * number_iterations)], color='blue', alpha=0.4, label=r'$\delta^{2}$H' + u' \u2030 (VSMOW)', normed='True')
        #		plt.axvline(x=actual_snow_ratio_long_term, label='Groundwater recharged from snowmelt (long term)', color='red')
        #		plt.axvline(x=actual_snow_ratio_short_term, label='Groundwater recharged from snowmelt (short term)', color='black')
        #		plt.xlim(0., 1.)
        #		plt.grid(linestyle='dotted')
        #		plt.xlabel("Fraction of snow in groundwater", fontsize=14)
        #		plt.ylabel("Normalised frequency", fontsize=14)
        #		plt.legend()
        #		plt.tight_layout()
        #		path = outputpath + "Figures/posterior_RAIN_" + str(rain_eff) + "_SNOW_" + str(snow_eff) + ".jpeg"
        #		plt.savefig(path, dpi=300)
        #		plt.close()
        #		print (path)

        del df

        snow_eff += 0.1

    rain_eff += 0.1

#################################################################################################################################
