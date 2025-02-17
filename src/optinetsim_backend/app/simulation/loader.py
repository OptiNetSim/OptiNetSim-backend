from pathlib import Path
from typing import Union, Dict, List

from gnpy.tools.json_io import network_from_json, _equipment_from_json

# Project imports
from src.optinetsim_backend.app.database.models import NetworkDB, EquipmentLibraryDB

_examples_dir = Path(__file__).parent / 'example-data'
DEFAULT_EXTRA_CONFIG = {"std_medium_gain_advanced_config.json": _examples_dir/"std_medium_gain_advanced_config.json",
                        "Juniper-BoosterHG.json": _examples_dir/"Juniper-BoosterHG.json"}

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
    network_json['network_name'] = network['network_name']
    network_json['elements'] = [
        {key: value for key, value in element.items()}
        for element in network['elements']
    ]
    network_json['connections'] = [
        {key: value for key, value in element.items()}
        for element in network['connections']
    ]
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
    # print(network_json)
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


def load_equipment_from_database(user_id, network_id, extra_config_filenames: List[Path] = []) -> dict:
    """
    从数据库中加载指定库ID的所有设备，并合并额外的配置文件。

    :param user_id: 用户ID
    :param network_id: 网络ID
    :param extra_config_filenames: 额外的配置文件列表
    :return: 设备配置字典
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

    # 初始化一个空字典，用于存储所有设备
    equipment_json = {}

    # 遍历每个器件库ID
    for library_id in library_ids:
        # 从数据库中查找指定库ID的设备
        library = EquipmentLibraryDB.find_by_id(library_id)

        # 遍历当前库的每一类设备
        for eq_category, eq_list in library['equipments'].items():
            if eq_category not in equipment_json:
                # 如果总设备字典中还没有这个类别，则直接添加
                equipment_json[eq_category] = eq_list.copy()  # 使用 copy 防止后续修改原列表
            else:
                # 如果已经存在，则将列表合并（扩展列表）
                equipment_json[eq_category].extend(eq_list)

    # 添加SI和Span配置信息
    equipment_json['SI'] = [network['SI'].copy()]
    equipment_json['Span'] = [network['Span'].copy()]

    # 加载额外的配置文件
    extra_configs = DEFAULT_EXTRA_CONFIG
    if extra_config_filenames:
        extra_configs = {f.name: f for f in extra_config_filenames}
        for k, v in DEFAULT_EXTRA_CONFIG.items():
            extra_configs[k] = v
    # print(extra_configs)
    # 使用合并的配置文件返回设备配置
    return _equipment_from_json(equipment_json, extra_configs)

def load_sim_parameters_from_database(user_id, network_id):
    """
    从数据库中加载仿真参数。
    :param user_id: 用户ID
    :param network_id: 网络ID
    :return: 仿真参数，如果未找到则返回None
    """
    # 从数据库中查找指定网络ID的网络配置
    network = NetworkDB.find_by_network_id(user_id, network_id)
    if not network:
        return None

    return network['simulation_config'].copy()