import argparse
import logging
import sys
from math import ceil
from numpy import mean
from pathlib import Path
from copy import deepcopy

import gnpy.core.ansi_escapes as ansi_escapes
from gnpy.core.elements import Transceiver, Fiber, RamanFiber, Roadm
from gnpy.core.utils import automatic_nch, watt2dbm, dbm2watt, pretty_summary_print, per_label_average
import gnpy.core.exceptions as exceptions
from gnpy.core.parameters import SimParams
from gnpy.core.utils import lin2db, pretty_summary_print, per_label_average, watt2dbm
from gnpy.topology.request import (ResultElement, jsontocsv, BLOCKING_NOPATH)
from gnpy.tools.plots import plot_baseline, plot_results
from gnpy.tools.worker_utils import designed_network, transmission_simulation, planning
from gnpy.tools.json_io import (load_equipment, load_network, load_json, load_requests, save_network,
                                requests_from_json, save_json, load_initial_spectrum)

# Project imports
from src.optinetsim_backend.app.simulation.loader import (
    load_network_from_database,
    load_spectral_information_from_database,
    load_span_information_from_database,
)
from src.optinetsim_backend.app.simulation.sim_params import generate_simulation_parameters


# Simulate the network
def simulate_network(user_id, network_id, source_uid, destination_uid, initial_spectrum=None):
    # Load the network from the database
    graph,library_ids = load_network_from_database(user_id, network_id)
    equipment = load_equipment_from_database(user_id, library_ids)
    transceivers = {n.uid: n for n in graph.nodes() if isinstance(n, Transceiver)}

    if not transceivers:
        return 'No transceivers found in the network'
    if len(transceivers) < 2:
        return 'At least two transceivers are needed to simulate the network'

    # Find exact match for source and destination
    source = transceivers.pop(source_uid, None)
    destination = transceivers.pop(destination_uid, None)

    # Load spectral information from the database
    network_SI = load_spectral_information_from_database(user_id, network_id)

    # Load span information from the database
    network_Span = load_span_information_from_database(user_id, network_id)

    # # Debug
    # print('Network SI:', network_SI)
    # print('Network Span:', network_Span)

    # Load the simulation parameters
    sim_params = generate_simulation_parameters(user_id, network_id, source, destination, network_SI, network_Span)

    # TODO: Add the code to simulate the network using the simulation parameters


# Debug
if __name__ == '__main__':
    simulate_network('678eb752758dcc9974b2603d', '678eb79f758dcc9974b2603e',
                     'source_uid', 'destination_uid')
    print('Simulation completed successfully')
