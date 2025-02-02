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


def transceiver_loader(user_id, element_config):
    """
    将网络元素配置转换为对应的元素节点。

    :param user_id: 用户ID
    :param element_config: 网络元素配置
    :return: 转换后的元素节点
    """
    # 复制元素配置并移除不必要的字段
    config_dict = deepcopy(element_config)
    """
    deepcopy(element_config): 
    这是一个函数调用，它接受一个参数element_config，这个参数是一个字典，
    包含了网络元素的配置信息。deepcopy函数会创建一个新的字典，这个新字典的内容与element_config完全相同，
    但是它们是两个独立的对象，对新字典的任何修改都不会影响原始的element_config。
    """
    config_dict.pop('type')
    config_dict.pop('name')
    config_dict.pop('library_id')
    config_dict.pop('type_variety')
    # 返回转换后的元素节点
    return elements.Transceiver(**config_dict)# 将字典中的键值对解包为关键字参数



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
        # # Debug
        # print('Element config', element_config)
        # print('Params', element_config['params'])
        # print('temp', temp)
        # print('Type of temp', type(temp))
        # print('extra_params', extra_params)
        # print('Type of extra_params', type(extra_params))
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
    print(config_dict)
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


def convert_to_element_node(user_id, element_config):
    """
    将网络元素配置转换为对应的元素节点。

    :param user_id: 用户ID
    :param element_config: 网络元素配置
    :return: 转换后的元素节点
    """
    # 获取网络元素的类型
    element_type = element_config['type']
    # 根据元素类型调用相应的加载器函数
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
    # 如果元素类型未知，则抛出异常
    else:
        raise ConfigurationError(f'Unknown network equipment "{element_type}"')


def load_network_from_database(user_id, network_id):
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
    # 创建一个有向图（DiGraph）
    g = DiGraph()

    # 用于存储所有的器件库ID
    library_ids = set()

    # 遍历网络配置中的每个元素
    for element_config in network['elements']:
        # 提取library_id并加入集合
        library_ids.add(element_config['library_id'])
        # 将元素配置转换为元素节点（对象），并添加到有向图中
        g.add_node(convert_to_element_node(user_id, element_config))

    # 创建一个字典，用于存储节点的UID和节点对象
    nodes = {k.uid: k for k in g.nodes()}

    # 遍历网络配置中的每个连接
    for cx in network['connections']:
        # 获取连接的起始节点和终止节点
        from_node, to_node = cx['from_node'], cx['to_node']
        try:
            # 如果起始节点是光纤（Fiber），则获取光纤的长度作为边的权重
            if isinstance(nodes[from_node], elements.Fiber):
                edge_length = nodes[from_node].params.length
            # 否则，将边的权重设置为0.01
            else:
                edge_length = 0.01
            # 在有向图中添加一条边，连接起始节点和终止节点，并设置边的权重
            g.add_edge(nodes[from_node], nodes[to_node], weight=edge_length)
        # 如果起始节点或终止节点未在有向图中找到，则抛出异常
        except KeyError:
            msg = f'can not find {from_node} or {to_node} defined in {cx}'
            raise NetworkTopologyError(msg)

    # 返回转换后的有向图
    return g, library_ids


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


def load_equipment_from_database(user_id, library_ids):
    """
    从数据库中加载指定库ID的所有设备。
    :param user_id: 用户ID
    :param library_ids: 库ID列表
    :return: 设备列表
    """
    # 初始化一个空列表，用于存储所有设备
    equipment = []

    for library_id in library_ids:
        # 从数据库中查找指定库ID的设备
        library = EquipmentLibraryDB.find_by_id(library_id)

        # 验证用户权限
        if not library or library['user_id'] != user_id:
            return {"message": f"Library with ID {library_id} not found or not authorized"}, 404

        # 获取设备列表并添加到返回结果
        equipment.extend(library['equipments'])

    return equipment, 200