import argparse
import logging
import sys
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


# Project imports
from src.optinetsim_backend.app.simulation.loader import (
    load_network_from_database,
    load_spectral_information_from_database,
    load_span_information_from_database,
load_equipment_from_database
)
from src.optinetsim_backend.app.simulation.sim_params import generate_simulation_parameters


# Simulate the network
def simulate_network(user_id, network_id, source_uid, destination_uid, initial_spectrum=None):
    equipment = load_equipment_from_database(user_id, network_id)
    network = load_network_from_database(user_id, network_id, equipment)
    plot_baseline(network)
    sim_params = {}
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

    # 精确匹配源和目的
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
    power_mode = equipment['Span']['default'].power_mode
    print('\n'.join([f'功率模式设置为 {power_mode}',
                     '=> 可在网络 Span 中修改该配置']))
    try:
        #print(nodes_list, loose_list)
        network, req, ref_req = designed_network(equipment, network, source.uid, destination.uid,
                                                 nodes_list=nodes_list, loose_list=loose_list,
                                                 args_power=0,
                                                 initial_spectrum=initial_spectrum,
                                                 no_insert_edfas=False,)
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
    for path, power_dbm in zip(propagations_for_path, powers_dbm):
        if power_mode:
            print(f'跨段输入光功率参考 = {ansi_escapes.cyan}{power_dbm:.2f} '
                  + f'dBm{ansi_escapes.reset}:')
        else:
            print('\n在 {ansi_escapes.cyan}增益模式{ansi_escapes.reset} 下传播：无法手动设置功率')
        if len(powers_dbm) == 1:
            for elem in path:
                print(elem)
            if power_mode:
                print(f'\n跨段输入光功率参考为 {power_dbm:.2f} dBm 时的传输结果：')
            else:
                print(f'\n传输结果：')
            print(f'  最终GSNR（0.1 nm）: {ansi_escapes.cyan}{mean(destination.snr_01nm):.02f} dB{ansi_escapes.reset}')
        else:
            print(path[-1])

if __name__ == '__main__':
    simulate_network('678eb752758dcc9974b2603d', '67a83f2109f8bdef32408844',
                     '67a84b51d61a87d997ddb187', '67a84b93be16bccc748e6e76')
    print('仿真成功完成')
