from copy import deepcopy
from typing import Union, List, Tuple
from numpy import linspace
from networkx import DiGraph

from gnpy.core.utils import automatic_nch, watt2dbm, dbm2watt, pretty_summary_print, per_label_average
from gnpy.core.equipment import trx_mode_params
from gnpy.core.network import add_missing_elements_in_network, design_network
from gnpy.core import exceptions
from gnpy.core.info import SpectralInformation
from gnpy.topology.spectrum_assignment import build_oms_list, pth_assign_spectrum, OMS
from gnpy.topology.request import correct_json_route_list, deduplicate_disjunctions, requests_aggregation, \
    compute_path_dsjctn, compute_path_with_disjunction, ResultElement, PathRequest, Disjunction, \
    compute_constrained_path, propagate
from gnpy.tools.json_io import requests_from_json, disjunctions_from_json

# Project imports
from src.optinetsim_backend.app.database.models import NetworkDB, EquipmentLibraryDB


# Generate transceiver mode parameters
def generate_trx_mode_params(user_id, network_id, network_SI, trx_type_variety='', trx_mode=''):
    trx_params = {}
    # default transponder characteristics
    # mainly used with transmission_main_example.py
    default_trx_params = {
        'f_min': network_SI['f_min'],
        'f_max': network_SI['f_max'],
        'baud_rate': network_SI['baud_rate'],
        'spacing': network_SI['spacing'],
        'OSNR': None,
        'penalties': {},
        'bit_rate': None,
        'cost': None,
        'roll_off': network_SI['roll_off'],
        'tx_osnr': network_SI['tx_osnr'],
        'min_spacing': None,
        'equalization_offset_db': 0
    }
    # Undetermined transponder characteristics
    # mainly used with path_request_run.py for the automatic mode computation case
    undetermined_trx_params = {
        "format": "undetermined",
        "baud_rate": None,
        "OSNR": None,
        "penalties": None,
        "bit_rate": None,
        "roll_off": None,
        "tx_osnr": None,
        "min_spacing": None,
        "cost": None,
        "equalization_offset_db": 0
    }

    # TODO: Add the code to get information from the database and assign it to trx_params

    return trx_params


# Generate simulation parameters
def generate_simulation_parameters(user_id, network_id, source, destination, network_SI, network_Span):
    nodes_list = [destination]
    loose_list = ['STRICT']
    params = {
        'request_id': 'reference',
        'trx_type': '',
        'trx_mode': '',
        'source': source,
        'destination': destination,
        'bidir': False,
        'nodes_list': nodes_list,
        'loose_list': loose_list,
        'format': '',
        'path_bandwidth': 0,
        'effective_freq_slot': None,
        'nb_channel': automatic_nch(network_SI['f_min'], network_SI['f_max'],
                                    network_SI['spacing']),
        'power': dbm2watt(network_SI['power_dbm']),
        'tx_power': dbm2watt(network_SI['tx_power_dbm']) if 'tx_power_dbm' in network_SI else network_SI['power_dbm'],
    }
    trx_params = generate_trx_mode_params(user_id, network_id, network_SI)

    # TODO: Add the code to get information from the database and assign it to params


