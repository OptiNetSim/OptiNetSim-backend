import argparse
import logging
import sys
from pathlib import Path
from numpy import mean

import gnpy.core.ansi_escapes as ansi_escapes
from gnpy.core.elements import Transceiver, Fiber, RamanFiber, Roadm
from gnpy.core.utils import automatic_nch, watt2dbm, dbm2watt, pretty_summary_print, per_label_average
import gnpy.core.exceptions as exceptions
from gnpy.core.parameters import SimParams
from gnpy.core.utils import lin2db, pretty_summary_print, per_label_average, watt2dbm
from gnpy.topology.request import (ResultElement, jsontocsv, BLOCKING_NOPATH)
from gnpy.tools.plots import plot_baseline, plot_results
from gnpy.tools.worker_utils import designed_network, transmission_simulation, planning
from gnpy.tools.json_io import load_initial_spectrum,_spectrum_from_json

# Project imports
from src.optinetsim_backend.app.simulation.loader import (
    load_network_from_database,
    load_equipment_from_database,
    load_sim_parameters_from_database
)
from src.optinetsim_backend.app.simulation.sim_params import generate_simulation_parameters


# Simulate the network
def simulate_network(user_id, network_id, source_uid, destination_uid, plot=False, show_channels=False, spectrum: dict = None, power = 0, no_insert_edfas = False):
    equipment = load_equipment_from_database(user_id, network_id)
    network = load_network_from_database(user_id, network_id, equipment)
    if plot:
        plot_baseline(network)
    sim_params = load_sim_parameters_from_database(user_id, network_id)
    # print(sim_params)
    if next((node for node in network if isinstance(node, RamanFiber)), None) is not None:
        print(f'{ansi_escapes.red}调用错误:{ansi_escapes.reset} '
              f'RamanFiber 需要通过 --sim-params 传递仿真参数')
        sys.exit(1)
    SimParams.set_params(sim_params)

    transceivers = {n.uid: n for n in network.nodes() if isinstance(n, Transceiver)}
    if not transceivers:
        return '网络中未找到收发器'
    if len(transceivers) < 2:
        return '至少需要两个收发器才能进行网络仿真'

    source = transceivers.pop(source_uid, None)
    destination = transceivers.pop(destination_uid, None)
    #print('源节点:', source)
    #print('目标节点:', destination)
    nodes_list = []
    loose_list = []

    if not source:
        source = list(transceivers.values())[0]
        del transceivers[source.uid]
        print('No source node specified: picking random transceiver')

    if not destination:
        destination = list(transceivers.values())[0]
        nodes_list = [destination.uid]
        loose_list = ['STRICT']
        print('No destination node specified: picking random transceiver')

    initial_spectrum = None
    if spectrum:
        # use the spectrum defined by user for the propagation.
        # the nb of channel for design remains the one of the reference channel
        initial_spectrum = _spectrum_from_json(spectrum)
        print('User input for spectrum used for propagation instead of SI')
    power_mode = equipment['Span']['default'].power_mode
    print('\n'.join([f'功率模式设置为 {power_mode}',
                     '=> 可在网络 Span 中修改该配置']))
    try:
        #print(nodes_list, loose_list)
        network, req, ref_req = designed_network(equipment, network, source.uid, destination.uid,
                                                 nodes_list=nodes_list, loose_list=loose_list,
                                                 args_power=power,
                                                 initial_spectrum=initial_spectrum,
                                                 no_insert_edfas=no_insert_edfas,)
        path, propagations_for_path, powers_dbm, infos = transmission_simulation(equipment, network, req, ref_req)
    except exceptions.NetworkTopologyError as e:
        print(f'{ansi_escapes.red}Invalid network definition:{ansi_escapes.reset} {e}')
        sys.exit(1)
    except exceptions.ConfigurationError as e:
        print(f'{ansi_escapes.red}Configuration error:{ansi_escapes.reset} {e}')
        sys.exit(1)
    except exceptions.ServiceError as e:
        print(f'Service error: {e}')
        sys.exit(1)
    except ValueError:
        sys.exit(1)
    if plot:
        plot_results(network, path, source, destination)
    spans = [s.params.length for s in path if isinstance(s, RamanFiber) or isinstance(s, Fiber)]
    print(f'\n在 {source.uid} 和 {destination.uid} 之间有 {len(spans)} 段光纤，总长 {sum(spans) / 1000:.0f} 公里')
    print(f'\n正在计算 {source.uid} 到 {destination.uid} 的传播：')
    print(f'设计使用的参考值: (跨段输入光功率参考 = {watt2dbm(ref_req.power):.2f} dBm,\n'
          + f'                           通道间隔 = {ref_req.spacing * 1e-9:.2f} GHz\n'
          + f'                           通道数量 = {ref_req.nb_channel})')
    print('\n传播中的通道参数: (跨段输入光功率偏差 = '
          + f'{pretty_summary_print(per_label_average(infos.delta_pdb_per_channel, infos.label))} dB,\n'
          + '                      通道间隔 = '
          + f'{pretty_summary_print(per_label_average(infos.slot_width * 1e-9, infos.label))} GHz,\n'
          + '                      收发器输出功率 = '
          + f'{pretty_summary_print(per_label_average(watt2dbm(infos.tx_power), infos.label))} dBm,\n'
          + f'                      通道数量 = {infos.number_of_channels})')
    for mypath, power_dbm in zip(propagations_for_path, powers_dbm):
        if power_mode:
            print(f'跨段输入光功率参考 = {ansi_escapes.cyan}{power_dbm:.2f} '
                  + f'dBm{ansi_escapes.reset}:')
        else:
            print('\n以 {ansi_escapes.cyan}增益模式{ansi_escapes.reset} 传播：无法手动设置功率')
        if len(powers_dbm) == 1:
            for elem in mypath:
                print(elem)
                print(type(elem))
            if power_mode:
                print(f'\n跨段输入光功率参考的传输结果 = {power_dbm:.2f} dBm:')
            else:
                print('\n传输结果:')
            print(f'  最终 GSNR (0.1 nm): {ansi_escapes.cyan}{mean(destination.snr_01nm):.02f} dB{ansi_escapes.reset}')
        else:
            print(mypath[-1])

    if show_channels:
        print('\n线路末端每个通道的 GSNR 为:')
        print(
            '{:>5}{:>26}{:>26}{:>28}{:>28}{:>28}' .format(
                '通道 #',
                '通道频率 (THz)',
                '通道功率 (dBm)',
                'OSNR ASE (信号带宽, dB)',
                'SNR NLI (信号带宽, dB)',
                'GSNR (信号带宽, dB)'))
        for final_carrier, ch_osnr, ch_snr_nl, ch_snr in zip(
                infos.carriers, path[-1].osnr_ase, path[-1].osnr_nli, path[-1].snr):
            ch_freq = final_carrier.frequency * 1e-12
            ch_power = lin2db(final_carrier.power.signal * 1e3)
            print(
                '{:5}{:26.5f}{:26.2f}{:28.2f}{:28.2f}{:28.2f}' .format(
                    final_carrier.channel_number, round(
                        ch_freq, 5), round(
                        ch_power, 2), round(
                        ch_osnr, 2), round(
                        ch_snr_nl, 2), round(
                            ch_snr, 2)))

if __name__ == '__main__':
    simulate_network('678eb752758dcc9974b2603d', '67a83f2109f8bdef32408844',
                     '67a858fd55643b796290c2e2', '67a858fd55643b796290c2e4', False)
    print('仿真成功完成')
