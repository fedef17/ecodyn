#!/usr/bin/python3

import numpy as np
from matplotlib import pyplot as plt
import matplotlib.cm as cm
import scipy
import xarray as xr
import os
import csv

################################################################################################################
######################################## Useful data

datadir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/")

########## data on investment from IEA (2015 to 2023). https://www.iea.org/reports/world-energy-investment-2023/overview-and-key-findings

lista = '1074 1319 1132 1105 1129 1114 1137 1109 1225 1066 1259 839 1408 914 1617 1002 1740 1050'.split()
Ig_obs_all = np.array(lista[0::2]).astype(float)
If_obs = np.array(lista[1::2]).astype(float)

# Data on green investment for energy production only (only "Renewable power" in clean energy spending)
Ig_obs = np.array('331 340 351 377 451 494 517 596 659'.split()).astype(float)

Ig_obs = xr.DataArray(Ig_obs, dims = ["year"], coords = {"year": np.arange(2015, 2024)})
Ig_obs_all = xr.DataArray(Ig_obs_all, dims = ["year"], coords = {"year": np.arange(2015, 2024)})
If_obs = xr.DataArray(If_obs, dims = ["year"], coords = {"year": np.arange(2015, 2024)})

#######################

########## E_g/E, from 1965 to 2023 (source ourworldindata: https://ourworldindata.org/renewable-energy)
cose = '6.445519 6.516204 6.423987 6.3901453 6.32996 6.2402315 6.2751184 6.231038 5.98148 6.527657 6.5613737 6.2220235 6.216026 6.4746337 6.5883255 6.8036585 6.9859357 7.1871624 7.3960943 7.3479614 7.309479 7.2850266 7.1429477 7.10847 6.9876184 7.182692 7.301195 7.2864876 7.6539183 7.6321683 7.8718243 7.755703 7.847491 7.890869 7.8530593 7.8158455 7.552836 7.5668545 7.3342075 7.518 7.5638204 7.705343 7.7473364 8.245706 8.564856 8.797048 8.980997 9.414955 9.847355 10.218171 10.504495 10.980251 11.337292 11.743186 12.228147 13.404395 13.469198 14.119935 14.562141'.split()

Eg_ratio = np.array(cose).astype(float)/100.
# Eg_ratio.sel(year = slice(2015, 2024)).values = Eg_ratio[-9:]

Eg_ratio = xr.DataArray(Eg_ratio, dims = ["year"], coords = {"year": np.arange(1965, 2024)})

##### Data from: https://www.statista.com/statistics/1325507/oil-and-gas-industry-profits-worldwide/

fossil_profits = np.array([0.11, 0.14, 0.22, 0.91, 0.8 , 0.9 , 0.93, 0.88, 1.66, 1.84, 1.27, 
       0.72, 0.86, 0.85, 0.78, 0.37, 0.55, 0.5 , 0.69, 0.91, 0.47, 0.51, 
       0.52, 0.46, 0.49, 0.64, 0.55, 0.29, 0.46, 0.91, 0.73, 0.68, 0.84, 
       1.17, 1.63, 1.85, 1.92, 2.62, 1.41, 1.84, 2.69, 2.62, 2.43, 2.13, 
       1. , 0.79, 1.11, 1.61, 1.35, 0.87])

Pf_obs = xr.DataArray(fossil_profits, dims = ["year"], coords = {"year": np.arange(1971, 2021)})

#################################################################################################################
#################################################################################################################

def test():
    print('Library loaded')
    return

def load_obs():
    E_obs = xr.load_dataarray('Etot_hist_1965-2022.nc')
    E_obs /= E_obs.sel(year = 2000)

    co2 = xr.load_dataset('co2_emiss_1750-2022.nc')['co2']

    return E_obs, co2


### the model

def sigmoid(x, delta = 1):
    return 1/(1+np.exp(-x/delta))


def GDP(Y, growth = 0.01, invert_time = False, linear_gdp = None):
    # print('AAAAAAAAAA', Y, linear_gdp)
    if linear_gdp is None:
        if not invert_time:
            Y *= (1+growth)
        else:
            Y /= (1+growth)
    else:
        Y += linear_gdp

    return Y

def to_emissions(Ef):
    """
    Convert fossil energy to CO2 emissions
    """
    return 38.*Ef/Ef.sel(year = 2023)

def get_wb_gdp_data(datadir = datadir):
    with open(datadir + 'API_NY.GDP.MKTP.CD_DS2_en_csv_v2_6298258.csv', newline='') as csvfile:
        reader = csv.reader(csvfile)

        rows = []
        for row in reader:
            rows.append(row)

    rows = rows[5:]

    country = [ro[0] for ro in rows]
    ro_ok = np.where(np.array(country) == 'World')[0][0]
    row_wld = rows[ro_ok]

    gdp = np.array(row_wld[4:-1], dtype = float)
    years = np.arange(1960, 2023)

    gdp = xr.DataArray(gdp, dims = ["year"], coords = {"year": np.arange(1960, 2023)})

    return gdp

########################### parameters ###########################################################################

default_params = dict()
default_params['growth'] = 0.01 # economic growth
default_params['eps'] = 1 # energy efficiency

default_params['a'] = 1 # Energy production per unit of infrastructure/capital (green)
default_params['b'] = 1 # Energy production per unit of infrastructure/capital (fossil)
# default_params['a_linear'] = None # (h, m) a = mx + h

default_params['gamma_f'] = 0.5 # Energy price (fossil)
default_params['gamma_g'] = 0.5 # Energy price (green)
default_params['eta_g'] = 0.2 # eta_g*gamma : Costs of energy production (green) [0-1]
default_params['eta_f'] = 0.2 # eta_f*gamma : Costs of energy production (fossil) [0-1]
default_params['h_g'] = 0.5 # Exponent for cost scaling with energy (green) [0-1]
default_params['h_f'] = 0.5 # Exponent for cost scaling with energy (green) [0-1]

default_params['r_inv'] = 0.1 # Fraction of profit that is reinvested in energy infrastructure [0-1]
default_params['beta_0'] = 0.2 # Fraction of infrastructure investments guaranteed for green energy (e.g. subsidies) [0-1]
#default_params['beta_2'] = 0.8 # beta_0 + beta_2 sums to 1
default_params['delta_sig'] = 0.5

default_params['delta_g'] = 0.01 # Depreciation of infrastructure/capital (green)
default_params['delta_f'] = 0.01 # Depreciation of infrastructure/capital (fossil)

default_params['f_heavy'] = 0.1 # Fraction of total production not willing to go green (e.g. military, heavy industry) [0-1]

default_inicond = {'Y_ini' : 1, 'Kg_ini' : 0.1, 'Kf_ini' : 0.9}

fossil_capacity_util = 0.5 # E/E_max at start; for oil is 0.8 (data from energy institute), but unknown for coal and gas, so likely smaller than 0.8
inicond_2015 = {'Y_ini' : 1, 'Kg_ini' : Eg_ratio.sel(year = 2015).values, 'Kf_ini' : (1-Eg_ratio.sel(year = 2015).values)/fossil_capacity_util} # from 2015
inicond_2000 = {'Y_ini' : 1, 'Kg_ini' : Eg_ratio.sel(year = 2000).values, 'Kf_ini' : (1-Eg_ratio.sel(year = 2000).values)/fossil_capacity_util} # Allowing more fossil capacity at start to avoid scarcity

def inicond_yr(year):
    inicond = {'Y_ini' : 1, 'Kg_ini' : Eg_ratio.sel(year = year).values, 'Kf_ini' : (1-Eg_ratio.sel(year = year).values)/fossil_capacity_util}
    return inicond

### Best fit in fit_linearY.ipynb
best_params = default_params.copy()

best_params.update({'growth': 0.0209418049925536, 
                    'beta_0': -0.2831097084724121,
                    'r_inv': 0.11684169484450775,
                    'a': 0.9418414596187906,
                    'delta_sig': 0.47990969261681554
                    })

# Params that give best fit using data of green energy share (2000-2023) and share of green energy investment (2015-2023). Cost function of energy investment is weighted at 0.1 (I_weight). Note delta_sig is at the lowest bound.
best_params_old = {'growth': 0.01877564045416566,
 'eps': 1,
 'a': 1,
 'b': 1,
 'gamma_f': 0.5,
 'gamma_g': 0.5751197750514625,
 'eta_g': 0.2,
 'eta_f': 0.2,
 'h_g': 0.5,
 'h_f': 0.5,
 'r_inv': 0.1,
 'beta_0': -0.1149135946421199,
 'delta_sig': 0.3,
 'delta_g': 0.01,
 'delta_f': 0.01,
 'f_heavy': 0.1}

# Same but with I_weight = 1, which gives slightly worse energy share fit (and faster transition!)
best_params_old_Iw1 = {'growth': 0.017055428532726295,
 'eps': 1,
 'a': 1,
 'b': 1,
 'gamma_f': 0.5,
 'gamma_g': 0.6460875554154768,
 'eta_g': 0.2,
 'eta_f': 0.2,
 'h_g': 0.5,
 'h_f': 0.5,
 'r_inv': 0.1,
 'beta_0': -0.1792655638830066,
 'delta_sig': 0.3,
 'delta_g': 0.01,
 'delta_f': 0.01,
 'f_heavy': 0.1}

########################### parameters ###########################################################################

def plot_cdf_beta(beta_0, prof_ratio, delta_sig):
    x = np.linspace(-3, 3)

    plt.plot(x, cdf(x, sigma = delta_sig))

    return

def cdf(x, mu = 0., sigma = 1.):
    # Compute the integral using the cumulative distribution function (CDF)
    cdf = 0.5 * (1 + scipy.special.erf((x - mu) / (sigma * np.sqrt(2))))
    return cdf


def beta_fun(beta_0, prof_ratio, delta_sig = 1., ftype = 'cdf'):
    """
    Defines fraction of green investment: should be limited between 0 and 1.

    New function cdf assumes gaussian investment around a mean that changes with expected profit and external factors:
        - investment is done randomly and represented by a gaussian distribution
        - the mean value is zero for equal expected profit, or can be different from zero
        - the integral below/above zero gives the two investment ratios

        the dynamics is governed by the ratio between the shift from zero of the mean and the width of the gaussian

        beta_0 is also a displacement
    """
    
    if ftype == 'cdf':
        beta = cdf(0., mu = -(beta_0 + prof_ratio), sigma = delta_sig)
    else:
        beta_2 = 1 - beta_0 # sums to 1
        beta = (beta_0 + beta_2*sigmoid(prof_ratio, delta = delta_sig)) 

    return beta


def prof_ratio(Pg, Pf, Kg, Kf):
    """
    Estimates the ratio of profits per unit investment (normalized).
    """
    return (Pg/Kg - Pf/Kf)/(Pg/Kg+Pf/Kf)
    #return (Pg/Kg - Pf/Kf)/((Pg+Pf)/(Kg+Kf))

def forward_step(Y, Kg, Kf, params = default_params, rule = 'maxgreen', betafun_type = 'cdf', verbose = False, raise_bnd_err = False, linear_gdp = None):
    """
    A single iteration of the model.
    """
    success = 0

    #### params ####
    growth = params['growth']
    eps = params['eps']
    a = params['a']
    b = params['b']
    gamma_g = params['gamma_g']
    gamma_f = params['gamma_f']
    eta_g = params['eta_g']
    eta_f = params['eta_f']
    h_g = params['h_g']
    h_f = params['h_f']
    r_inv = params['r_inv']
    beta_0 = params['beta_0']
    delta_sig = params['delta_sig']
    delta_g = params['delta_g']
    delta_f = params['delta_f']
    f_heavy = params['f_heavy']
    #########
    if verbose: print('params: ', params)

    # Energy and infrastructure
    Eg_max = a * Kg # a = 1
    Ef_max = b * Kf # b time dependent, exog. should decrease to 0

    ## Total production?
    # opt 1: exogenous growing Y, tot energy proportional to Y
    E = eps * Y

    if Eg_max + Ef_max < E: 
        success = 2
        if verbose: print(f'Energy scarcity! {Eg_max} {Ef_max} {E}')
        # raise ValueError(f'Energy scarcity! {Eg_max} {Ef_max} {E}')

    if rule == 'maxgreen':
        Eg = Eg_max
        Ef = E-Eg
        if Eg > E:
            Eg = E
            Ef = 0.
    elif rule == 'proportional':
        Eg = Kg/(Kg+Kf) * E
        Ef = Kf/(Kg+Kf) * E
    elif rule == 'fair':
        if Ef_max >= E/2.:
            Ef = E/2.
        else:
            Ef = Ef_max
        Eg = E - Ef
    elif rule == 'whole_capacity': # This makes Y useless
        Eg = Eg_max
        Ef = Ef_max
    elif rule == 'fossil_constraint': # military and heavy industry keep using fossil
        Ef_min = f_heavy * Y
        if E-Ef_min < Eg_max:
            Ef = Ef_min
            Eg = E-Ef_min
        else:
            Eg = Eg_max
            Ef = E-Eg
    
    if E == Eg: 
        if verbose: print('Transition completed!')
        success = 1

    # opt 2: endogenous Y (Dafermos)
    #Y = l * E_max

    ## Profit of energy production
    Pg = gamma_g * (Eg - eta_g * Eg**h_g)
    Pf = gamma_f * (Ef - eta_f * Ef**h_f)
    if Pf < 0.: Pf = gamma_f * (1 - eta_f) * Ef # linearity for small Ef
    if Pg < 0.: Pg = gamma_g * (1 - eta_g) * Eg # linearity for small Eg

    ## Investment in energy production
    pr = prof_ratio(Pg, Pf, Kg, Kf)
    beta = beta_fun(beta_0, pr, delta_sig = delta_sig, ftype = betafun_type)
    
    Ig = beta * r_inv * (Pg + Pf)
    If = (1-beta) * r_inv * (Pg + Pf)
    if verbose: print(('check: ' + 8*'{:10.2f}').format(beta, pr, Eg, Ef, Pg, Pf, Ig, If))

    ## for next step
    ## Capital/infrastructure
    if verbose and Ig < Kg*delta_g: print(f'Green infrastructure decreasing! {Ig} < {Kg*delta_g}')
    if verbose and If < Kf*delta_f: print(f'Fossil infrastructure decreasing! {If} < {Kf*delta_f}')
    Kg = Ig + Kg * (1-delta_g)
    Kf = If + Kf * (1-delta_f)
    Y = GDP(Y, growth = growth, linear_gdp = linear_gdp)

    Kg, Kf, Eg, Ef, beta, E, Y = check_bounds(Kg, Kf, Eg, Ef, beta, E, Y, raise_err = raise_bnd_err)

    # else: # going backwards
    #     Kg = (Kg - Ig)/(1-delta_g)
    #     Kf = (Kf - If)/(1-delta_f)
    #     Y = GDP(Y, growth = growth, invert_time = True)

    return Y, Kg, Kf, E, Eg, Ef, Ig, If, Pg, Pf, success


def define_Eg(E, Kg, Kf, a, b, f_heavy, rule = 'maxgreen', verbose = False):
    # Energy and infrastructure
    Eg_max = a * Kg # a = 1
    Ef_max = b * Kf # b time dependent, exog. should decrease to 0

    if Eg_max + Ef_max < E: 
        success = 2
        if verbose: print(f'Energy scarcity! {Eg_max} {Ef_max} {E}')
        # raise ValueError(f'Energy scarcity! {Eg_max} {Ef_max} {E}')

    if rule == 'maxgreen':
        Eg = Eg_max
        Ef = E-Eg
        if Eg > E:
            Eg = E
            Ef = 0.
    elif rule == 'proportional':
        Eg = Kg/(Kg+Kf) * E
        Ef = Kf/(Kg+Kf) * E
    elif rule == 'whole_capacity': # This makes Y useless
        Eg = Kg
        Ef = Kf
    elif rule == 'fossil_constraint': # military and heavy industry keep using fossil
        Ef_min = f_heavy * Y
        if E-Ef_min < Eg_max:
            Ef = Ef_min
            Eg = E-Ef_min
        else:
            Eg = Eg_max
            Ef = E-Eg
    
    return Eg, Ef


def backward_step(Y, Kg, Kf, params = default_params, rule = 'maxgreen', betafun_type = 'cdf', verbose = False, raise_bnd_err = False):
    """
    A single iteration of the model.
    """
    success = 0

    #### params ####
    growth = params['growth']
    eps = params['eps']
    a = params['a']
    b = params['b']
    gamma_g = params['gamma_g']
    gamma_f = params['gamma_f']
    eta_g = params['eta_g']
    eta_f = params['eta_f']
    h_g = params['h_g']
    h_f = params['h_f']
    r_inv = params['r_inv']
    beta_0 = params['beta_0']
    delta_sig = params['delta_sig']
    delta_g = params['delta_g']
    delta_f = params['delta_f']
    f_heavy = params['f_heavy']
    #########

    ## Total production?
    # opt 1: exogenous growing Y, tot energy proportional to Y
    Y = GDP(Y, growth = growth, invert_time=True)
    E = eps * Y

    # Loop to define K
    max_iter = 20
    ii = 0
    thres = 1e-4
    Kgit = Kg
    Kfit = Kf
    cond = True
    while cond and ii < max_iter:
        if verbose: print('ITeration:', ii)
        Eg, Ef = define_Eg(E, Kgit, Kfit, a, b, f_heavy, rule = rule)

        ## Profit of energy production of previous step
        Pg = gamma_g * (Eg - eta_g * Eg**h_g)
        Pf = gamma_f * (Ef - eta_f * Ef**h_f)
        if Pf < 0.: Pf = gamma_f * (1 - eta_f) * Ef # linearity for small Ef
        if Pg < 0.: Pg = gamma_g * (1 - eta_g) * Eg # linearity for small Eg

        ## Investment in energy production
        beta = beta_fun(beta_0, (Pg/Kg - Pf/Kf)/(Pg/Kg+Pf/Kf), delta_sig = delta_sig, ftype = betafun_type)
        #if verbose: print(beta, (Pg/Kg - Pf/Kf)/(Pf/Kf), Eg, Ef, Pg, Pf)
        
        Ig = beta * r_inv * (Pg + Pf)
        If = (1-beta) * r_inv * (Pg + Pf)
        #if verbose: print(Ig, If)

        Kgit_old = Kgit
        Kfit_old = Kfit

        Kgit = (Kg - Ig)/(1-delta_g)
        Kfit = (Kf - If)/(1-delta_f)

        Kgit, Kfit, Eg, Ef, beta, E, Y = check_bounds(Kgit, Kfit, Eg, Ef, beta, E, Y, raise_err = raise_bnd_err)

        if verbose: print(Kgit, Kgit_old)

        cond = abs((Kgit-Kgit_old)/Kgit) > thres
        ii +=1
    
    Kg = Kgit
    Kf = Kfit
    
    # if E == Eg: 
    #     if verbose: print('Transition completed!')
    #     success = 1

    # ## Profit of energy production of previous step
    # Pg = gamma_g * (Eg - eta_g * Eg**h_g)
    # Pf = gamma_f * (Ef - eta_f * Ef**h_f)
    # if Pf < 0.: Pf = gamma_f * (1 - eta_f) * Ef # linearity for small Ef
    # if Pg < 0.: Pg = gamma_g * (1 - eta_g) * Eg # linearity for small Eg

    # ## Investment in energy production
    # beta_2 = 1 - beta_0 # sums to 1
    # beta = (beta_0 + beta_2*sigmoid((Pg/Kg - Pf/Kf)/(Pf/Kf), delta = delta_sig)) # fraction of green investment: should be limited between 0 and 1
    # if verbose: print(beta, (Pg/Kg - Pf/Kf)/(Pf/Kf), Eg, Ef, Pg, Pf)
    
    # Ig = beta * r_inv * (Pg + Pf)
    # If = (1-beta) * r_inv * (Pg + Pf)
    # if verbose: print(Ig, If)

    # Kg = (Kg - Ig)/(1-delta_g)
    # Kf = (Kf - If)/(1-delta_f)

    return Y, Kg, Kf, E, Eg, Ef, Ig, If, Pg, Pf, success


def check_bounds(Kg, Kf, Eg, Ef, beta, E, Y, raise_err = False):
    input_vec = np.array([Kg, Kf, Eg, Ef, beta, E, Y])
    nams = np.array('Kg, Kf, Eg, Ef, beta, E, Y'.split())
    mins = np.array([0, 0, 0, 0, 0, 0, 0])
    maxs = np.array([Kg, Kf, E, E, 1., E, Y])

    if np.all(input_vec >= mins) and np.all(input_vec <= maxs):
        pass
    elif np.any(input_vec < mins):
        if raise_err: 
            raise ValueError('Below threshold!', nams[np.where(input_vec < mins)])
        else:
            print('Resetting to min val: ', nams[np.where(input_vec < mins)])
            input_vec[np.where(input_vec < mins)] = mins[np.where(input_vec < mins)]
    elif np.any(input_vec > maxs):
        if raise_err:
            raise ValueError('Above threshold!', nams[np.where(input_vec > maxs)])
        else:
            print('Resetting to max val: ', nams[np.where(input_vec > maxs)])
            input_vec[np.where(input_vec > maxs)] = maxs[np.where(input_vec > maxs)]

    return list(input_vec)


def set_params(params, years, verbose = False):
    okpar = default_params.copy()
    scenario_pars = []

    for par in okpar:
        if type(params[par]) == float:
            if params[par] != default_params[par]:
                if verbose: print(f'Changing default for param {par}')
                okpar[par] = params[par]
        else:
            okpar[par] = params[par]

        if isinstance(params[par], xr.core.dataarray.DataArray) or isinstance(params[par], np.ndarray):
            scenario_pars.append(par)

        # if f'{par}_linear' in params:
        #     if verbose: print(f'Setting value of {par} with linear slope!')
        #     intercept, slope = params[f'{par}_linear']
        #     okpar[par] = intercept + slope*(years - years[0]) # scenario
    
    if len(scenario_pars) > 0:
        allow_param_scenario = scenario_pars
    else:
        allow_param_scenario = None
    
    return okpar, allow_param_scenario


def run_model(inicond = default_inicond, params = default_params, n_iter = 100, rule = 'maxgreen', betafun_type = 'cdf', verbose = True, run_backwards = False, raise_bnd_err = False, year_ini = None, extend_constant = False, linear_gdp = None):
    """

    Runs the model. Returns list of lists of outputs: [Y, Kg, Kf, E, Eg, Ef]  (can be improved!)

    Rules are for energy partition when potential production exceeds demand (see forward_step function).

    allow_param_scenario removed. if parameters are arrays or dataarrays, this flag is automatically activated.

    """
    if year_ini is None:
        raise ValueError(f'{year_ini} not set!')

    Y = inicond['Y_ini']
    Kg = inicond['Kg_ini']
    Kf = inicond['Kf_ini']

    years = np.arange(year_ini, year_ini + n_iter)
    params_ok, allow_param_scenario = set_params(params, years)
    okpar = params.copy()

    resu = []
    for i in range(n_iter):
        if allow_param_scenario is not None:
            for par in allow_param_scenario:
                if verbose: 
                    print(f'using scenario for param {par}:')
                    print(okpar[par])
                if isinstance(params_ok[par], xr.core.dataarray.DataArray):
                    ymax = params_ok[par].year.max().values
                    yok = min(year_ini + i, ymax)
                    print(yok, ymax)
                    okpar[par] = params_ok[par].sel(year = yok).values
                else:
                    print('checkpar', i)
                    okpar[par] = params_ok[par][i]

        if not run_backwards:
            Y, Kg, Kf, E, Eg, Ef, Ig, If, Pg, Pf, success = forward_step(Y, Kg, Kf, params = okpar, verbose = verbose, rule = rule, betafun_type = betafun_type, raise_bnd_err= raise_bnd_err, linear_gdp = linear_gdp)
        else:
            Y, Kg, Kf, E, Eg, Ef, Ig, If, Pg, Pf, success = backward_step(Y, Kg, Kf, params = okpar, verbose = verbose, rule = rule, betafun_type = betafun_type, raise_bnd_err=raise_bnd_err)

        resu.append([Y, Kg, Kf, E, Eg, Ef, Ig, If, Pg, Pf])
        if success == 0: 
            continue
        elif success == 1:
            if verbose: print(f'Transition completed at time: {i}!')
            break
        elif success == 2:
            if verbose: print(f'Energy scarcity at time: {i}!')
            break
    
    if extend_constant:
        if len(resu) < n_iter:
            print(f'Too short! extending up to {year_ini + n_iter}')
            resu = np.stack(resu)
            last_row = resu[-1, :]        
            repeated = np.repeat(last_row[np.newaxis, :], n_iter - resu.shape[0], axis = 0)
            resu = np.concatenate([resu, repeated], axis = 0)

    resu = rebuild_resu(resu, run_backwards = run_backwards)
    
    if not run_backwards:
        if success == 1: 
            resu['success'] = True
            resu['year_zero'] = i
            resu['year_peak'] = np.argmax(resu['Ef'])

            for ye in range(resu['year_peak'], len(resu['Ef'])):
                if resu['Ef'][ye] <= resu['Ef'][resu['year_peak']]/2.: break
            resu['year_halved'] = ye
            if verbose: print('Peak fossil: {}'.format(resu['year_peak']))
            if verbose: print('Halved fossil: {}'.format(resu['year_halved']))
        else:
            resu['success'] = False
            resu['year_zero'] = np.nan
            resu['year_peak'] = np.nan
            resu['year_halved'] = np.nan
    
    if year_ini is not None:
        resu = build_resu_ds(resu, year_ini = year_ini)

    return resu


def rebuild_resu(resu, run_backwards = False):
    if isinstance(resu, list):
        resu = np.stack(resu)
    Ys = resu[:, 0]
    Kgs = resu[:, 1]
    Kfs = resu[:, 2]
    E = resu[:, 3]
    Eg = resu[:, 4]
    Ef = resu[:, 5]
    Ig = resu[:, 6]
    If = resu[:, 7]
    Pg = resu[:, 8]
    Pf = resu[:, 9]
    if run_backwards:
        Ys = Ys[::-1]
        Kgs = Kgs[::-1]
        Kfs = Kfs[::-1]
        E = E[::-1]
        Eg = Eg[::-1]
        Ef = Ef[::-1]
        Ig = Ig[::-1]
        If = If[::-1]
        Pg = Pg[::-1]
        Pf = Pf[::-1]

    ok_resu = dict()
    ok_resu['Y'] = Ys
    ok_resu['Kg'] = Kgs
    ok_resu['Kf'] = Kfs
    ok_resu['E'] = E
    ok_resu['Eg'] = Eg
    ok_resu['Ef'] = Ef
    ok_resu['Ig'] = Ig
    ok_resu['If'] = If
    ok_resu['Pg'] = Pg
    ok_resu['Pf'] = Pf
    ok_resu['Ig_ratio'] = Ig/(Ig+If)
    ok_resu['Eg_ratio'] = Eg/E

    return ok_resu


def build_resu_ds(resu, year_ini):
    data_vars = {vnam : (['year'], resu[vnam]) for vnam in resu.keys() if isinstance(resu[vnam], np.ndarray)}
    scalars = {vnam : resu[vnam] for vnam in resu.keys() if vnam not in data_vars}
    for ke in scalars:
        if 'year' in ke: scalars[ke] += year_ini
    years = np.arange(year_ini, year_ini + len(resu['Y']))

    ds = xr.Dataset(data_vars = data_vars, coords={'year': years}, attrs = scalars)

    return ds


def cost_function(parset, parnames = ['beta_0', 'gamma_g', 'growth', 'delta_sig'], params = default_params.copy(), year_ini = 2015, inicond = inicond_2015, verbose = False, all_green = False, I_weight = 1., obs = None, linear_gdp = None):
    """
    Fit model to (year_ini - 2025) obs.
    """

    if verbose:
        print(all_green, I_weight, obs, linear_gdp)
        
    n_iter = 2025 - year_ini
    years = np.arange(year_ini, 2025)

    pardict = {par: val for par, val in zip(parnames, parset)}
    print('---------------------')
    print(pardict)

    for par in pardict:
        if 'intercept' in par:
            short_nam = par[:par.rfind('_')]
            if f'{short_nam}_slope' in parnames:
                params[short_nam] = pardict[f'{short_nam}_intercept'] + pardict[f'{short_nam}_slope']*(years - year_ini) # scenario
            else:
                raise ValueError(f'{short_nam}_slope not in parnames!')
        elif 'slope' in par:
            short_nam = par[:par.rfind('_')]
            if f'{short_nam}_intercept' not in parnames:
                raise ValueError(f'{short_nam}_intercept not in parnames!')
        else:
            params[par] = pardict[par]        

    # for parval, pnam in zip(ok_parset, ok_names):
    #         params[pnam] = parval
    
    params['gamma_f'] = params['gamma_g']
    #print('----')
    #print(params)
    #print('---------------------')
    resu = run_model(inicond = inicond, params = params, n_iter = n_iter, year_ini = year_ini, verbose = verbose, rule = 'maxgreen', extend_constant = True, linear_gdp = linear_gdp)
    #print(len(resu['Eg']))

    # What to fit on
    if obs is None:
        obs = dict()
        if all_green:
            obs['Ig_ratio'] = Ig_obs_all/(Ig_obs_all+If_obs)
        else:
            obs['Ig_ratio'] = Ig_obs/(Ig_obs+If_obs)
        obs['Eg_ratio'] = Eg_ratio
    
    if I_weight < 1.:
        weights = {'Ig_ratio': I_weight, 'Eg_ratio': 1.-I_weight}
    else:
        weights = None

    cost = costfun(resu, obs, weights = weights)

    #cost = costfun_1524(resu, year_ini = year_ini, I_weight = I_weight, all_green = all_green)
    if verbose: print(f'Cost: {cost}')

    return cost


def calc_sens_param(param_name, frac_pert = 0.5, var_range = None, inicond = default_inicond, params = default_params, n_iter = 100, n_pert = 5):
    """
    Calculates sensitivity to a single parameter. Computes multiple times the model and returns the trajectories.
    """
    if frac_pert < 0 or frac_pert > 1: raise ValueError('var_range should be between 0 and 1')

    if var_range is None: var_range = [default_params[param_name]*(1-frac_pert), default_params[param_name]*(1+frac_pert)]

    nominal = run_model(inicond = inicond, params = params, n_iter = n_iter, verbose = False)
    
    vals = np.linspace(var_range[0], var_range[1], n_pert)
    
    all_resu = []
    var_params = params.copy()
    for val in vals:
        var_params[param_name] = val
        resu = run_model(inicond = inicond, params = var_params, n_iter = n_iter, verbose = False)

        all_resu.append(resu)

    #plot_resu(resu)
    return vals, nominal, all_resu


def get_colors_from_colormap(n_col, colormap_name='RdBu_r'):
    cmap = cm.get_cmap(colormap_name)
    colors = np.array([cmap(i/(n_col-1)) for i in range(n_col)])
    #print(colors)
    return colors


def plot_sens_param(vals, nominal, all_resu, plot_type = 'tuning'):
    """
    Plots output of calc_sens_param.
    """

    if plot_type == 'dynamics':
        fig = plt.figure()
        resu = nominal
        plt.plot(resu['Kf'] + resu['Kg'], label = 'Total', color = 'violet')
        plt.plot(resu['Kf'], label = 'Fossil', color = 'black')
        plt.plot(resu['Kg'], label = 'Green', color = 'green')

        for resu in all_resu:
            plt.plot(resu['Kf'] + resu['Kg'], color = 'violet', ls = ':', lw = 0.5)
            plt.plot(resu['Kf'], color = 'black', ls = ':', lw = 0.5)
            plt.plot(resu['Kg'], color = 'green', ls = ':', lw = 0.5)

        plt.xlabel('time')
        plt.ylabel('Energy infrastructure')
        plt.legend()

        fig2 = plt.figure()
        resu = nominal
        plt.plot(resu['E'], label = 'Total', color = 'violet')
        plt.plot(resu['Ef'], label = 'Fossil', color = 'black')
        plt.plot(resu['Eg'], label = 'Green', color = 'green')
        for resu in all_resu:
            plt.plot(resu['E'], label = 'Total', color = 'violet', ls = ':', lw = 0.5)
            plt.plot(resu['Ef'], label = 'Fossil', color = 'black', ls = ':', lw = 0.5)
            plt.plot(resu['Eg'], label = 'Green', color = 'green', ls = ':', lw = 0.5)

        plt.xlabel('time')
        plt.ylabel('Energy production')
        plt.legend()
    
    elif plot_type == 'tuning':
        fig = plt.figure()
        resu = nominal
        # Ig = np.diff(resu['Kg'])
        # If = np.diff(resu['Kf'])
        Ig = resu['Ig']
        If = resu['If']

        plt.plot((Ig/(Ig+If))[:20], label = 'model', color = 'black')
        plt.plot(Ig_obs/(Ig_obs+If_obs), label = 'obs', color = 'orange')

        colors = get_colors_from_colormap(len(all_resu))

        for resu, col in zip(all_resu, colors):
            # Ig = np.diff(resu['Kg'])
            # If = np.diff(resu['Kf'])
            Ig = resu['Ig']
            If = resu['If']
            plt.plot((Ig/(Ig+If))[:20], color = col, ls = '--', lw = 1)

            # plt.annotate(f'({x_annotate}, {y_annotate:.2f})', xy=(x_annotate, y_annotate), xytext=(x_annotate + 1, y_annotate - 0.5), arrowprops=dict(facecolor='black', shrink=0.05))

        plt.xlabel('time')
        plt.ylabel('Green share of energy investment (beta)')
        plt.legend()

        fig2 = plt.figure()
        resu = nominal
        plt.plot((resu['Eg']/resu['E'])[:20], label = 'model', color = 'black')
        plt.plot(Eg_ratio.sel(year = slice(2015, 2024)).values, label = 'obs', color = 'orange')
        
        for resu, col in zip(all_resu, colors):
            plt.plot((resu['Eg']/resu['E'])[:20], color = col, ls = '--', lw = 1)

        plt.xlabel('time')
        plt.ylabel('Share of renewable energy')
        plt.legend()

    fig3 = plt.figure()
    year_zeros = [resu['year_zero'] for resu in all_resu]
    year_peaks = [resu['year_peak'] for resu in all_resu]
    year_halveds = [resu['year_halved'] for resu in all_resu]
    for val, yze, ype, yha, col in zip(vals, year_zeros, year_peaks, year_halveds, colors):
        plt.scatter(val, yze, color = col, marker = 'o')
        plt.scatter(val, ype, color = col, marker = '>')
        plt.scatter(val, yha, color = col, marker = 'x')
    
    plt.xlabel('value')
    plt.ylabel('years')
    plt.legend()

    return fig, fig2, fig3


def costfun(resu, obs, weights = None, verbose = False):
    """
    Generic cost function for whatever is inside obs. Resu is a dataset and obs is a dict of dataarrays with 'year' axis.

    If given, weights should be a dictionary with weights for all variables in obs.
    """

    cost = []

    if verbose:
        print('Resu:')
        print(resu)

        print('Obs:')
        print(obs)

    for var in obs:
        wvar = 1
        if weights is not None:
            if var in weights:
                wvar = weights[var]
            else:
                wvar = 1.
        
        cc = wvar*((resu[var]-obs[var])**2).sum().values
        cost.append(cc)

    return np.sum(cost)


def costfun_1524(resu, year_ini = 2015, I_weight = 1., all_green = False):
    """
    Calcs cost function to observed data for 2015-2024.

    year_ini indicates first year of model sim
    I_weight is the weight to give to the "investment part" of the cost function relative to the energy share part
    """
    Ig = resu['Ig']
    If = resu['If']

    if isinstance(resu, xr.core.dataset.Dataset):
        sim_pr = (Ig/(Ig+If)).sel(year = slice(2015, 2024)).values
        sim_eg = (resu['Eg']/resu['E']).sel(year = slice(2015, 2024)).values
    else:
        ind_ini = 2015 - year_ini
        ind_fin = ind_ini + 9
        sim_pr = (Ig/(Ig+If))[ind_ini:ind_fin]
        sim_eg = (resu['Eg']/resu['E'])[ind_ini:ind_fin]

    if all_green:
        cost_I = 1.e4*np.sum((sim_pr - (Ig_obs_all/(Ig_obs_all+If_obs)))**2)
    else:
        cost_I = 1.e4*np.sum((sim_pr - (Ig_obs/(Ig_obs+If_obs)))**2)

    cost_Eg = np.sum((sim_eg - Eg_ratio.sel(year = slice(2015, 2024)).values)**2)

    return I_weight * cost_I + cost_Eg


def costfun_hist(resu, year_ini = 2000, I_weight = 1., all_green = False):
    """
    Calcs cost function to observed data, using both energy share (1965-2024) and investment share (2015-2024).

    year_ini indicates first year of model sim
    I_weight is the weight to give to the "investment part" of the cost function relative to the energy share part

    """
    ind_ini = 2015 - year_ini
    ind_fin = ind_ini + 9

    Ig = resu['Ig']
    If = resu['If']

    #print(ind_ini, ind_fin, len(Ig))

    if all_green:
        cost_I = 1.e4*np.sum(((Ig/(Ig+If))[ind_ini:ind_fin] - (Ig_obs_all/(Ig_obs_all+If_obs)))**2)
    else:
        cost_I = 1.e4*np.sum(((Ig/(Ig+If))[ind_ini:ind_fin] - (Ig_obs/(Ig_obs+If_obs)))**2)

    ind_ini = 1965 - year_ini
    if ind_ini < 0: ind_ini = 0
    ind_fin = ind_ini + len(Eg_ratio)
    if ind_fin > len(resu['Eg']): ind_fin = len(resu['Eg'])-1

    #print(ind_ini, ind_fin, len(Ig))

    ind_obs_ini = year_ini - 1965
    ind_obs_fin = ind_obs_ini + len(resu['Eg'])-1

    #print(ind_obs_ini, ind_obs_fin, len(Ig))

    cost_Eg = np.sum(((resu['Eg']/resu['E'])[ind_ini:ind_fin] - Eg_ratio[ind_obs_ini:ind_obs_fin])**2)

    return I_weight * cost_I + cost_Eg


def plot_resuvsobs_ds(resu, obs, year_ok = slice(2000, 2030), var_names = None):
    """
    Generic plot function for whatever is inside obs. Resu is a dataset and obs is a dict of dataarrays with 'year' axis.
    """

    figs = []
    for var in obs:
        fig = plt.figure()
        obspl = obs[var].sel(year = year_ok).plot(label = 'obs', color = 'orange')
        resupl = resu[var].sel(year = year_ok).plot(label = 'model', color = 'black')

        plt.xlabel('year')
        if var_names is not None:
            plt.ylabel(var_names[var])
        else:
            plt.ylabel(var)

        plt.legend()
        figs.append(fig)

    return figs


def plot_resuvsobs(resu, year_ini = 2000, year_fin = 2100, maxlen = None, all_green = False, mod_col = 'orange', obs_col = 'black', obs_name = 'obs', mod_name = 'model'):#, ind_ini = 0, ind_fin = 20):
    """
    Plots outputs vs observed green investment and green energy share.
    """

    if maxlen is not None:
        year_ini = resu.year[0]
        year_fin = resu.year[0] + maxlen

    if not isinstance(resu, xr.core.dataset.Dataset):
        resu = build_resu_ds(resu, year_ini)

    fig = plt.figure()
    # Ig = np.diff(resu['Kg'])
    # If = np.diff(resu['Kf'])

    #totle = min(maxlen, len(Ig))
    #resu = resu.isel(year = slice(0, maxlen))
    resu = resu.sel(year = slice(year_ini, year_fin))

    Ig = resu['Ig']
    If = resu['If']

    resu['beta'] = resu.Ig/(resu.If + resu.Ig)

    resu.beta.plot(label = mod_name, color = mod_col)
    # plt.plot(np.arange(year_ini, year_ini + totle), (Ig/(Ig+If))[:totle], label = mod_name, color = mod_col)
    if all_green:
        print('Plotting original data of green investment from world bank')
        Ig_ratio_obs = Ig_obs_all/(Ig_obs_all+If_obs)
        Ig_ratio_obs.sel(year = slice(year_ini, year_fin)).plot(label = obs_name, color = obs_col)
        #plt.plot(np.arange(2015, 2024), Ig_obs_all/(Ig_obs_all+If_obs), label = obs_name, color = obs_col)
    else:
        print('Plotting only data regarding investment on green power production (only part of what world bank considers green investment)')
        Ig_ratio_obs = Ig_obs/(Ig_obs+If_obs)
        Ig_ratio_obs.sel(year = slice(year_ini, year_fin)).plot(label = obs_name, color = obs_col)
        #plt.plot(np.arange(2015, 2024), Ig_obs/(Ig_obs+If_obs), label = obs_name, color = obs_col)

    plt.xlabel('year')
    plt.ylabel(r'Green share of energy investment ($\beta$)')
    plt.legend()

    fig2 = plt.figure()
    resu['Eg_ratio'] = resu['Eg']/resu['E']
    Eg_ratio.sel(year = slice(year_ini, year_fin)).plot(label = obs_name, color = obs_col)
    resu['Eg_ratio'].plot(label = mod_name, color = mod_col)
    # plt.plot(np.arange(year_ini, year_ini + totle), (resu['Eg']/resu['E'])[:totle], label = mod_name, color = mod_col)
    # plt.plot(np.arange(year_ini, 2024), Eg_ratio[-(2024-year_ini):], label = obs_name, color = obs_col)

    plt.xlabel('year')
    plt.ylabel('Share of renewable energy')
    plt.legend()

    return fig, fig2


def plot_hist(resu, year_ini = 1950, maxlen = 50):
    """
    Plots outputs vs observed green investment and green energy share.
    """

    fig = plt.figure()
    #Ig = np.diff(resu['Kg'])
    #If = np.diff(resu['Kf'])
    Ig = resu['Ig']
    If = resu['If']

    totle = min(maxlen, len(Ig))

    plt.plot(np.arange(year_ini, year_ini + totle), (Ig/(Ig+If))[:totle], label = 'model', color = 'black')
    plt.plot(np.arange(2015, 2024), Ig_obs/(Ig_obs+If_obs), label = 'obs', color = 'orange')

    plt.xlabel('time')
    plt.ylabel('Green share of energy investment (beta)')
    plt.legend()

    fig2 = plt.figure()
    plt.plot(np.arange(year_ini, year_ini + totle), (resu['Eg']/resu['E'])[:totle], label = 'model', color = 'black')
    plt.plot(np.arange(1965, 2024), Eg_ratio, label = 'obs', color = 'orange')

    plt.xlabel('time')
    plt.ylabel('Share of renewable energy')
    plt.legend()

    return fig, fig2


def plot_resu(resu, year_ini = None, title = None):
    if not isinstance(resu, xr.core.dataset.Dataset):
        if year_ini is not None:
            resu = build_resu_ds(resu, year_ini)
            xax = resu.year
        else:
            xax = np.arange(len(resu['E']))
    else:
        xax = resu.year

    fig, ax = plt.subplots()
    plt.plot(xax, resu['Kf'] + resu['Kg'], label = 'Total')
    plt.plot(xax, resu['Kf'], label = 'Fossil')
    plt.plot(xax, resu['Kg'], label = 'Green')
    if year_ini is not None:
        plt.xlabel('year')
    else:
        plt.xlabel('time')
    plt.ylabel('Energy infrastructure')
    plt.legend()
    if title is not None:
        plt.title(title)

    fig2, ax2 = plt.subplots()
    plt.plot(xax, resu['E'], label = 'Total')
    plt.plot(xax, resu['Ef'], label = 'Fossil')
    plt.plot(xax, resu['Eg'], label = 'Green')

    if not np.isnan(resu.year_peak):
        ax2.axvline(resu.year_peak, color = 'indianred', lw = 0.5, ls = ':')
    if not np.isnan(resu.year_halved):
        ax2.axvline(resu.year_halved, color = 'grey', lw = 0.5, ls = ':')
    if not np.isnan(resu.year_zero):
        ax2.axvline(resu.year_zero, color = 'forestgreen', lw = 0.5, ls = ':')

    if year_ini is not None:
        plt.xlabel('year')
    else:
        plt.xlabel('time')
    plt.ylabel('Energy production')
    plt.legend()
    
    if title is not None:
        plt.title(title)

    return fig, fig2