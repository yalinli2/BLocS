#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  9 13:11:47 2021

@author: daltonstewart
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  8 14:10:33 2021

@author: daltonstewart
"""

#Import modules
import biosteam as bst
from biorefineries import sugarcane as sc
from biorefineries import lipidcane as lc
from chaospy import distributions as shape
from biosteam.evaluation.evaluation_tools import triang
import incentives as ti
import numpy as np
import pandas as pd
import os

#Import state scenario data
folder = os.path.dirname(__file__)
st_data_file = os.path.join(folder, 'state_scenarios_for_import.xlsx')
st_data = pd.read_excel(st_data_file, index_col=[0])

states = [
          'Florida',
          'Texas',      
           ]

states_w_inc = [
                'Hawaii',            
                'Louisiana',             
                ]

all_states = [
          'Florida',        
          'Texas',      
          'Hawaii',       
          'Louisiana',        
           ]

tea = lc.create_tea(sc.sugarcane_sys, ti.IncentivesTEA)
model = bst.Model(sc.sugarcane_sys, exception_hook='raise')

tea.fuel_tax = 0.
tea.sales_tax = 0.
tea.federal_income_tax = 0.35
tea.state_income_tax = 0.065
tea.property_tax = 0.013
tea.utility_tax = 0.
tea.incentive_numbers = ()
tea.ethanol_product = sc.ethanol
tea.ethanol_group = sc.ethanol_production_units
tea.feedstock = sc.sugarcane
tea.BT = sc.BT
bst.PowerUtility.price = 0.0685

def MFSP_getter(state):
    def MFSP():
        tea.state_income_tax = st_data.loc[state]['Income Tax Rate (decimal)']
        tea.property_tax = st_data.loc[state]['Property Tax Rate (decimal)']
        tea.fuel_tax = st_data.loc[state]['State Motor Fuel Tax (decimal)']
        tea.sales_tax = st_data.loc[state]['State Sales Tax Rate (decimal)']
        bst.PowerUtility.price = st_data.loc[state]['Electricity Price (USD/kWh)']
        tea.F_investment = st_data.loc[state]['Location Capital Cost Factor (dimensionless)']
        tea.incentive_numbers = ()
        return 2.98668849 * tea.solve_price(sc.ethanol)
    return MFSP

def MFSP_w_inc_getter(state):
    def MFSP():
        tea.state_income_tax = st_data.loc[state]['Income Tax Rate (decimal)']
        tea.property_tax = st_data.loc[state]['Property Tax Rate (decimal)']
        tea.fuel_tax = st_data.loc[state]['State Motor Fuel Tax (decimal)']
        tea.sales_tax = st_data.loc[state]['State Sales Tax Rate (decimal)']
        bst.PowerUtility.price = st_data.loc[state]['Electricity Price (USD/kWh)']
        tea.F_investment = st_data.loc[state]['Location Capital Cost Factor (dimensionless)']
        
        if state == 'Alabama':
            tea.incentive_numbers = (8,9)
        elif state == 'Colorado':
            tea.incentive_numbers = (10,)
        elif state == 'Hawaii':
            tea.incentive_numbers = (11,)
        elif state == 'Iowa':
            tea.incentive_numbers = (1,12,21)
        elif state == 'Kansas':
            tea.incentive_numbers = (2,)
        elif state == 'Kentucky':
            tea.incentive_numbers = (13,14,22)
        elif state == 'Louisiana':
            tea.incentive_numbers = (15,)
        elif state == 'Michigan':
            tea.incentive_numbers = (3,)
        elif state == 'Montana':
            tea.incentive_numbers = (4,23)
        elif state == 'Nebraska':
            tea.incentive_numbers = (5,)
        elif state == 'New Mexico':
            tea.incentive_numbers = (7,)
        elif state == 'Oregon':
            tea.incentive_numbers = (6,)
        elif state == 'South Carolina':
            tea.incentive_numbers = (16,17)
        elif state == 'Utah':
            tea.incentive_numbers = (18,)
        elif state == 'Virginia':
            tea.incentive_numbers = (19,)
            
        return 2.98668849 * tea.solve_price(sc.ethanol)
    return MFSP

@model.metric(name='Utility cost', units='10^6 USD/yr')
def get_utility_cost():
    return tea.utility_cost / 1e6

@model.metric(name='Net electricity production', units='MWh/yr')
def get_electricity_production():
    return sum(i.power_utility.rate for i in sc.sugarcane_sys.units) * tea.operating_hours/1000

@model.metric(name="Baseline MFSP", units='USD/gal')
def MFSP_baseline():
    tea.incentive_numbers = ()
    MFSP = 2.98668849 * tea.solve_price(sc.ethanol)
    return MFSP

for state in states:
    element = f"{state}"
    model.metric(MFSP_getter(state), 'MFSP', 'USD/gal', element)
    
for state in states_w_inc:
    element = f"{state}"
    model.metric(MFSP_w_inc_getter(state), 'MFSP', 'USD/gal', element)


### Create parameter distributions ============================================
# Feedstock prices, distribution taken from Yoel's example
sugarcane = sc.sugarcane
FP_L = sugarcane.price * 0.9 # min price
FP_U = sugarcane.price * 1.1 # max price

# Gasoline prices, USD/gal
GP_dist = shape.Uniform(2.103, 2.934)

# Location capital cost factors
LCCF_dist = shape.Triangle(0.82, 1, 2.56)

# Electricty generation efficiency
EGeff_dist = shape.Triangle(0.7,0.85,0.9)

### Add Parameters =============================================================
# Feedstock price
@model.parameter(element=sugarcane, kind='isolated', units='USD/kg',
                  distribution=shape.Uniform(FP_L, FP_U))
def set_feed_price(feedstock_price):
    sugarcane.price = feedstock_price
    
#: WARNING: these distributions are arbitrary and a thorough literature search
#: and an analysis of U.S. ethanol price projections should be made 
#: to include these

# Plant capacity
@model.parameter(element=sugarcane, kind='isolated', units='kg/hr',
                  distribution=triang(sugarcane.F_mass))
def set_plant_capacity(plant_capacity):
    sugarcane.F_mass = plant_capacity

# Boiler efficiency
@model.parameter(element=sc.BT, units='%', distribution=triang(sc.BT.boiler_efficiency))
def set_boiler_efficiency(boiler_efficiency):
    sc.BT.boiler_efficiency = boiler_efficiency    

# Turbogenerator efficiency
@model.parameter(element=sc.BT, units='%', distribution=EGeff_dist)
def set_turbogenerator_efficiency(turbo_generator_efficiency):
    sc.BT.turbogenerator_efficiency = turbo_generator_efficiency

# Fermentation efficiency
# fermentation = cs.R303
# @model.parameter(
#     element=fermentation, distribution=shape.Triangle(0.85, 0.90, 0.95),
#     baseline=fermentation.efficiency,
# )
# def set_fermentation_efficiency(efficiency):
#     fermentation.efficiency= efficiency

# Lipid fraction
# Originally 0.10, but this is much to optimistic. In fact,
# even 0.05 is optimistic.
# model.parameter(lc.set_lipid_fraction, element=lc.lipidcane,
#                 distribution=triang(0.05), baseline=0.05)

### Plot across coordinates
np.random.seed(1688)
N_samples = 1
rule = 'L' # For Latin-Hypercube sampling
samples = model.sample(N_samples, rule)
model.load_samples(samples)
model.evaluate()
table = model.table
