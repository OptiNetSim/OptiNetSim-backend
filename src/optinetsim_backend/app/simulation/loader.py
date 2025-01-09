from networkx import DiGraph
from logging import getLogger
from pathlib import Path
import json
from collections import namedtuple
from numpy import arange
from copy import deepcopy

from gnpy.core import elements
from gnpy.core.equipment import trx_mode_params, find_type_variety
from gnpy.core.exceptions import ConfigurationError, EquipmentConfigError, NetworkTopologyError, ServiceError
from gnpy.core.science_utils import estimate_nf_model
from gnpy.core.info import Carrier
from gnpy.core.utils import automatic_nch, automatic_fmax, merge_amplifier_restrictions, dbm2watt
from gnpy.core.parameters import DEFAULT_RAMAN_COEFFICIENT, EdfaParams, MultiBandParams
from gnpy.topology.request import PathRequest, Disjunction, compute_spectrum_slot_vs_bandwidth
from gnpy.topology.spectrum_assignment import mvalue_to_slots
from gnpy.tools.convert import xls_to_json_data
from gnpy.tools.service_sheet import read_service_sheet
from gnpy.tools.json_io import Amp, merge_equalization

# Project imports
from src.optinetsim_backend.app.database.models import NetworkDB, EquipmentLibraryDB

# Logger
_logger = getLogger(__name__)


# Transceiver element loader
def transceiver_loader(user_id, element_config):
    config_dict = deepcopy(element_config)
    config_dict.pop('type')
    config_dict.pop('name')
    config_dict.pop('library_id')
    config_dict.pop('type_variety')
    return elements.Transceiver(**config_dict)


# Multiband amplifier element loader
def multiband_amplifier_loader(user_id, element_config):
    library_id = element_config['library_id']
    # Copy element config and remove unnecessary fields
    config_dict = deepcopy(element_config)
    config_dict.pop('type')
    config_dict.pop('name')
    config_dict.pop('library_id')
    # Load extra parameters from equipment library
    # If type_variety is not provided, use default values
    if 'type_variety' in element_config:
        element_type_variety = element_config['type_variety']
        extra_params = EquipmentLibraryDB.find_by_type_variety(user_id, library_id, 'Edfa', element_type_variety)
        if not extra_params:
            raise ConfigurationError(f'Multiband amplifier "{element_type_variety}" not found in library')
        extra_params = extra_params['params']
        temp = element_config.setdefault('params', {})
        temp = merge_amplifier_restrictions(temp, deepcopy(extra_params))
        config_dict['params'] = temp
    else:
        extra_params = None
        temp = element_config.setdefault('params', {})
        temp = merge_amplifier_restrictions(temp, deepcopy(MultiBandParams.default_values))
        config_dict['params'] = temp
    # if config does not contain any amp list create one
    amps = element_config.setdefault('amplifiers', [])
    for amp in amps:
        amp_variety = amp['type_variety']
        amp_extra_params = EquipmentLibraryDB.find_by_type_variety(user_id, library_id, 'Edfa', amp_variety)
        temp = amp.setdefault('params', {})
        temp = merge_amplifier_restrictions(temp, amp_extra_params)
        amp['params'] = temp
        amp['type_variety'] = amp_variety
    #
    if not amps and extra_params is not None:
        # the amp config does not contain the amplifiers operational settings, but has a type_variety
        # defined so that it is possible to create the template of amps for design for each band. This
        # defines the default design bands.
        # This loop populates each amp with default values, for each band
        for band in extra_params.bands:
            params = {k: v for k, v in Amp.default_values.items()}
            # update frequencies with band values
            params['f_min'] = band['f_min']
            params['f_max'] = band['f_max']
            amps.append({'params': params})
    return elements.Multiband_amplifier(**config_dict)


# Fused element loader
def fused_loader(user_id, element_config):
    config_dict = deepcopy(element_config)
    config_dict.pop('type')
    config_dict.pop('name')
    config_dict.pop('library_id')
    config_dict.pop('type_variety')
    return elements.Fused(**config_dict)


# Fiber element loader
def fiber_loader(user_id, element_config):
    config_dict = deepcopy(element_config)
    config_dict.pop('type')
    config_dict.pop('name')
    config_dict.pop('library_id')
    # Load extra parameters from equipment library
    library_id = element_config['library_id']
    if 'type_variety' in element_config:
        element_type_variety = element_config['type_variety']
        extra_params = EquipmentLibraryDB.find_by_type_variety(user_id, library_id, 'Fiber', element_type_variety)
        if not extra_params:
            raise ConfigurationError(f'Fiber "{element_type_variety}" not found in library')
        extra_params = extra_params['params']
        temp = element_config.setdefault('params', {})
        # Debug
        print('Element config', element_config)
        print('Params', element_config['params'])
        print('temp', temp)
        print('Type of temp', type(temp))
        print('extra_params', extra_params)
        print('Type of extra_params', type(extra_params))
        temp = merge_amplifier_restrictions(temp, deepcopy(extra_params))
        config_dict['params'] = temp
    else:
        raise ConfigurationError(
            f'The {element_config["type"]} element {element_config["name"]} does not have a type_variety'
            '\nplease check it is properly defined in the eqpt_config json file')
    return elements.Fiber(**config_dict)


# Raman fiber element loader
def raman_fiber_loader(user_id, element_config):
    config_dict = deepcopy(element_config)
    config_dict.pop('type')
    config_dict.pop('name')
    config_dict.pop('library_id')
    # Load extra parameters from equipment library
    library_id = element_config['library_id']
    if 'type_variety' in element_config:
        element_type_variety = element_config['type_variety']
        extra_params = EquipmentLibraryDB.find_by_type_variety(user_id, library_id, 'Fiber', element_type_variety)
        if not extra_params:
            raise ConfigurationError(f'Fiber "{element_type_variety}" not found in library')
        extra_params = extra_params['params']
        temp = element_config.setdefault('params', {})
        temp = merge_amplifier_restrictions(temp, deepcopy(extra_params))
        config_dict['params'] = temp
    else:
        raise ConfigurationError(
            f'The {element_config["type"]} element {element_config["name"]} does not have a type_variety'
            '\nplease check it is properly defined in the eqpt_config json file')
    return elements.RamanFiber(**config_dict)


# Edfa element loader
def edfa_loader(user_id, element_config):
    library_id = element_config['library_id']
    # Copy element config and remove unnecessary fields
    config_dict = deepcopy(element_config)
    config_dict.pop('type')
    config_dict.pop('name')
    config_dict.pop('library_id')
    # Load extra parameters from equipment library
    if 'type_variety' in element_config:
        element_type_variety = element_config['type_variety']
        extra_params = EquipmentLibraryDB.find_by_type_variety(user_id, library_id, 'Edfa', element_type_variety)
        if not extra_params:
            raise ConfigurationError(f'Edfa "{element_type_variety}" not found in library')
        extra_params = extra_params['params']
        temp = element_config.setdefault('params', {})
        temp = merge_amplifier_restrictions(temp, deepcopy(extra_params))
        config_dict['params'] = temp
    else:
        config_dict['params'] = Amp.default_values
    return elements.Edfa(**config_dict)


# Roadm element loader
def roadm_loader(user_id, element_config):
    config_dict = deepcopy(element_config)
    config_dict.pop('type')
    config_dict.pop('name')
    config_dict.pop('library_id')
    # Load extra parameters from equipment library
    library_id = element_config['library_id']
    if 'type_variety' in element_config:
        element_type_variety = element_config['type_variety']
        extra_params = EquipmentLibraryDB.find_by_type_variety(user_id, library_id, 'Roadm', element_type_variety)
        if not extra_params:
            raise ConfigurationError(f'Roadm "{element_type_variety}" not found in library')
        extra_params = extra_params['params']
        temp = element_config.setdefault('params', {})
        extra_params = merge_equalization(temp, extra_params)
        temp = merge_amplifier_restrictions(temp, deepcopy(extra_params))
        config_dict['params'] = temp
    else:
        raise ConfigurationError(
            f'The {element_config["type"]} element {element_config["name"]} does not have a type_variety'
            '\nplease check it is properly defined in the eqpt_config json file')
    return elements.Roadm(**config_dict)


# Convert element config to element node
def convert_to_element_node(user_id, element_config):
    element_type = element_config['type']
    if element_type == 'Transceiver':
        return transceiver_loader(user_id, element_config)
    elif element_type == 'Multiband_amplifier':
        return multiband_amplifier_loader(user_id, element_config)
    elif element_type == 'Fused':
        return fused_loader(user_id, element_config)
    elif element_type == 'Fiber':
        return fiber_loader(user_id, element_config)
    elif element_type == 'RamanFiber':
        return raman_fiber_loader(user_id, element_config)
    elif element_type == 'Edfa':
        return edfa_loader(user_id, element_config)
    elif element_type == 'Roadm':
        return roadm_loader(user_id, element_config)
    else:
        raise ConfigurationError(f'Unknown network equipment "{element_type}"')


# Load network from database and convert to networkx graph
def load_network_from_database(user_id, network_id):
    network = NetworkDB.find_by_network_id(user_id, network_id)
    if not network:
        return None
    g = DiGraph()
    # Add elements to network
    for element_config in network['elements']:
        g.add_node(convert_to_element_node(user_id, element_config))

    nodes = {k.uid: k for k in g.nodes()}

    for cx in network['connections']:
        from_node, to_node = cx['from_node'], cx['to_node']
        try:
            if isinstance(nodes[from_node], elements.Fiber):
                edge_length = nodes[from_node].params.length
            else:
                edge_length = 0.01
            g.add_edge(nodes[from_node], nodes[to_node], weight=edge_length)
        except KeyError:
            msg = f'can not find {from_node} or {to_node} defined in {cx}'
            raise NetworkTopologyError(msg)

    return g


if __name__ == '__main__':
    # Load network from database
    network = load_network_from_database("6707bbb1a58be0ffa5d05618", "6707bbe8a58be0ffa5d05619")
    print(network)
