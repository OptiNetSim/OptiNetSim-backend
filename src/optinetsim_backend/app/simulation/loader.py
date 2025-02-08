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
from gnpy.tools.json_io import network_from_json, _equipment_from_json, Amp, merge_equalization, Fiber, Span, Roadm, SI, \
    Transceiver, RamanFiber, _check_fiber_vs_raman_fiber, _update_dual_stage, _update_band, \
    _roadm_restrictions_sanity_check

# Project imports
from src.optinetsim_backend.app.database.models import NetworkDB, EquipmentLibraryDB


def load_network_from_database(user_id, network_id, equipment):
    """
    从数据库中加载网络配置，并将其转换为一个有向图（DiGraph）。

    :param user_id: 用户ID
    :param network_id: 网络ID
    :return: 转换后的有向图（DiGraph）
    """
    # 从数据库中查找指定网络ID的网络配置
    network = NetworkDB.find_by_network_id(user_id, network_id)
    # 如果未找到网络配置，则返回None
    if not network:
        return None
    network_json = {}
    # 遍历 elements 列表中的每个元素
    for element in network_json['elements']:
        # 将 element_id 键名替换为 uid
        element['uid'] = element.pop('element_id')

        # 移除 name 和 library_id 键值对
        element.pop('name', None)
        element.pop('library_id', None)
    # 遍历 connections 列表中的每个元素
    for connection in network_json['connections']:
        # 移除 connection_id 键值对
        connection.pop('connection_id', None)
    # 打印修改后的 JSON 数据
    print(json.dumps(network_json, indent=4))
    # 返回转换后的有向图
    return network_from_json(network_json, equipment)


def load_spectral_information_from_database(user_id, network_id):
    """
    从数据库中加载光谱信息。

    :param user_id: 用户ID
    :param network_id: 网络ID
    :return: 光谱信息，如果未找到则返回None
    """
    # 从数据库中查找指定网络ID的网络配置
    network = NetworkDB.find_by_network_id(user_id, network_id)
    # 如果未找到网络配置，则返回None
    if not network:
        return None
    # 返回光谱信息
    return network['SI']


def load_span_information_from_database(user_id, network_id):
    """
    从数据库中加载跨度信息。

    :param user_id: 用户ID
    :param network_id: 网络ID
    :return: 跨度信息，如果未找到则返回None
    """
    # 从数据库中查找指定网络ID的网络配置
    network = NetworkDB.find_by_network_id(user_id, network_id)
    # 如果未找到网络配置，则返回None
    if not network:
        return None
    # 返回跨度信息
    return network['Span']


def load_equipment_from_database(user_id, network_id):
    """
    从数据库中加载指定库ID的所有设备。
    :param user_id: 用户ID
    :param library_ids: 库ID列表
    :return: 设备列表
    """
    # 从数据库中查找指定网络ID的网络配置
    network = NetworkDB.find_by_network_id(user_id, network_id)
    # 如果未找到网络配置，则返回None
    if not network:
        return None
    # 用于存储所有的器件库ID
    library_ids = set()

    # 遍历网络配置中的每个元素
    for element_config in network['elements']:
        # 提取library_id并加入集合
        library_ids.add(element_config['library_id'])
    # print(library_ids)
    # 初始化一个空列表，用于存储所有设备
    equipment_json = {}
    for library_id in library_ids:
        # 从数据库中查找指定库ID的设备
        library = EquipmentLibraryDB.find_by_id(library_id)
        # library['equipments'] 是一个字典，比如：
        # {'Edfa': [...], 'Fiber': [...], 'RamanFiber': [...], 'Roadm': [...], 'Transceiver': [...]}

        # 遍历当前库的每一类设备
        for eq_category, eq_list in library['equipments'].items():
            if eq_category not in equipment_json:
                # 如果总设备字典中还没有这个类别，则直接添加
                equipment_json[eq_category] = eq_list.copy()  # 使用 copy 防止后续修改原列表
            else:
                # 如果已经存在，则将列表合并（扩展列表）
                equipment_json[eq_category].extend(eq_list)
    equipment_json['SI'] = [network['SI'].copy()]
    equipment_json['Span'] = [network['Span'].copy()]
    # print(equipment_json)
    return _equipment_from_json(equipment_json, './default_edfa_config.json')
