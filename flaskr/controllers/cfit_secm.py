import math
import scipy.optimize
import numpy as np
import pandas as pd
import io
import os
import requests

# from . import UPLOAD_FOLDER


##################################   DATA  CURATOR   #########################################
def fit_data_Cornut(path, electrode_radius, Rg, iT_inf, K):
   # Workaround to let pandas read data directly from url
    if path:
        r = requests.get(path)
        open('temp.xls', 'wb').write(r.content)

        workbook = pd.read_excel('temp.xls')
    else:
        print("Wrong path!")
    
    
    current_values = [] # WILL STORE THE VALUES FROM THE 'Imon [1]' COLUMN OF THE EXCEL FILE

    for i in workbook.iloc[:,2]:
        current_values.append(i)

    current_values = current_values[20:] # Deletes the first points of the curve
                                            # its where the tip touches the surface and its not good for the fit

    distance_values = [] # WILL STORE THE VALUES FROM THE 'Distance [m]' COLUMN OF THE EXCEL FILE



    for v in workbook.iloc[:,1]:
        distance_values.append(v)

    distance_values = distance_values[20:] # also deletes the first points for the distance values
                                                # in order to have the same number of points in both arrays

    # In the given data-example, by not deleting the first 20-points the algorithm leads to an order of magnitude in error.


    ##################################  PREREQUISITES  #########################################


    global L_data
    global iT_data

    L_data = [] # Stores the values for normalized distance L=d/a - EXPERIMENTAL
    iT_data = [] # Stores the values for normalized current iT=iT/iT_inf - EXPERIMENTAL

    for x in distance_values:
        #value = x-zoffset
        L_data.append(x/float(electrode_radius))

    for y in current_values:
        iT_data.append(y/float(iT_inf))


    ############################  ALFA AND BETA CONSTANTS  #######################################

    alfa = math.log(2) + math.log(2)*(1- 2/math.pi*math.acos(1/Rg)) - math.log(2)*(1-(2/math.pi*math.acos(1/Rg))**2)
    beta = 1 + 0.639*(1-2/math.pi*math.acos(1/Rg))-0.186*(1-(2/math.pi*math.acos(1/Rg))**2)



    ############################    SIMULATED   CURVES     #######################################

    def cornut(L_data, K):

        iT_ins = ((2.08/Rg**0.358)*(L_data-(0.145/Rg)) + 1.585)/(2.08/(Rg**0.358)*(L_data+0.0023*Rg)+1.57+(math.log(Rg)/L_data)+2/(math.pi*Rg)*math.log(1+(math.pi*Rg)/(2*L_data)))
        #iT_insulated.append(iT_ins) # values are stored backwards to shape the graph as they happen
                            # in reality from 'infinite' distance to aprox. 0
                            # distance tip-to-substrate.

        #iT_cond (Eq. 18 - article)
        iT_cond = alfa + (math.pi/(4*beta*math.atan(L_data))) + ((1-alfa-1/(2*beta))*2/math.pi*math.atan(L_data))
    

        #iT_simulated (Eq. 21 - L,Rg,K)
        iT_sim = alfa + (math.pi/(4*beta*math.atan(L_data+1/K))) + ((1-alfa-1/(2*beta))*2/math.pi*math.atan(L_data+1/K)) + (iT_ins-1)/((1+2.47*Rg**(0.31)*L_data*K)*(1+L_data**(0.006*Rg+0.113)*K**(-0.0236*Rg+0.91)))
        return iT_sim


    ############################    LEAST SQ. FITTING     ######################################


    r = np.vectorize(cornut)

    p0 = [K]


    popt1, pcov = scipy.optimize.curve_fit(r, L_data, iT_data, p0=p0, method = 'lm') #calculates the popt and pcov for the experimental
                                                                                        # data provided by the user

    # whereas -popt gives the: array Optimal values for the parameters so that the sum of the squared residuals of f(xdata, *popt) - ydata is minimized
        # and -pcov returns the: 2d array The estimated covariance of popt. The diagonals provide the variance of the parameter estimate.

    popt = popt1[0] #Leave the parantheses

    # Although in order to also compute one standard deviation errors on the parameters use perr = np.sqrt(np.diag(pcov)). 

    E_sigma = np.sqrt(np.diag(pcov)) # Error parameter
    E_sigma = E_sigma[0] #Leave the parantheses



    ############################  PRINT THE RESULTS     ########################################

    # print('Kappa = {}'.format("{:.5f}".format(popt)),'\nCovariance = {}'.format(pcov[0]), '\nE_sigma = {}'.format("{:.5f}".format(E_sigma)))

    global iT_simulated
    iT_simulated = r(L_data, popt)

    global final_dataset
    final_dataset = {"L_data":L_data, 
                        "iT_experimental":iT_data,
                        "iT_simulated":iT_simulated}

    Kappa = '{}'.format("{:.5f}".format(popt))
    Chi2 = '{}'.format("{:.5f}".format(E_sigma))
    
   # 2 dataframes stored in-mem variables, which are later transfered to the blob storage using Azure's SDK 
    fitting_parameters = {'Kappa':[Kappa], 'Chi2':[Chi2]}
    global fit_params_df
    global fit_dataset_df
    fit_params_df = pd.DataFrame(fitting_parameters)
    fit_dataset_df = pd.DataFrame(final_dataset)
    print("Finished fitting.")
    return [fit_params_df, fit_dataset_df]

    
    #################################   THE END OF FITTING     ############################################


