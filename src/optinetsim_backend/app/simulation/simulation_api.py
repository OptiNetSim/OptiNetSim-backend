# coding: utf-8
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import request
from src.optinetsim_backend.app.simulation.core import simulate_network
from gnpy.core.utils import watt2dbm, per_label_average, mean
from src.optinetsim_backend.app.database.models import NetworkDB

def convert_to_spectrum_array(data, metric_name):
    """
    Convert dictionary format to array of objects with spectrum_band and metric value.
    
    Args:
        data (dict): Dictionary with spectrum band as key and metric value as value
        metric_name (str): Name of the metric value field in output
        
    Returns:
        list: Array of dictionaries with spectrum_band and metric value
    """
    return [
        {
            "spectrum_band": band,
            metric_name: str(value)
        }
        for band, value in data.items()
    ]

class SingleLinkSimulationResource(Resource):
    @jwt_required()
    def post(self):
        """
        单链路仿真接口：
        需要传递的 JSON 参数：
            - network_id: 网络ID
            - source_uid: 源收发器的 uid
            - destination_uid: 目标收发器的 uid
            - plot (可选): 是否生成图形，默认为 False
            - spectrum (可选): 仿真传输所用的频谱信息字典
            - power (可选): 跨段输入光功率参考，默认为 0
            - no_insert_edfas (可选): 是否禁用插入 EDFAs，默认为 False
        """
        '''
        示例：
        {
            "network_id": "67a83f2109f8bdef32408844",
            "source_uid": "67a858fd55643b796290c2e2",
            "destination_uid": "67a858fd55643b796290c2e4"
        }
        '''
        try:
            data = request.get_json()
        except Exception as e:
            return {"message": "请求体解析失败: " + str(e)}, 400

        # 检查必需参数
        network_id = data.get("network_id")
        source_uid = data.get("source_uid")
        destination_uid = data.get("destination_uid")
        if not network_id or not source_uid or not destination_uid:
            return {"message": "必须提供 network_id、source_uid 和 destination_uid 参数"}, 400

        # 获取可选参数
        plot = data.get("plot", False)
        spectrum = data.get("spectrum", None)
        power = data.get("power", 0)
        no_insert_edfas = data.get("no_insert_edfas", False)

        # 当前用户ID通过 JWT 获取
        user_id = get_jwt_identity()

        try:
            spans, infos, res_path, mypath, channel_data = simulate_network(
                user_id, network_id, source_uid, destination_uid,
                plot=plot,
                spectrum=spectrum,
                power=power,
                no_insert_edfas=no_insert_edfas
            )
            
            full_path_info = []
            for elem in mypath:
                element_id = elem.uid
                element_name = NetworkDB.find_element_name_by_id(network_id, element_id)
                replaced_str = str(elem).replace(elem.uid, element_name or elem.uid)
                
                # 解析字符串为字典
                element_dict = {}
                lines = replaced_str.split('\n')
                
                if lines:
                    # 处理第一行元素描述
                    element_dict["element"] = lines[0].strip()
                    
                    # 处理后续属性行
                    for line in lines[1:]:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # 分割键值对
                        if ':' in line:
                            key, value = line.split(':', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            # 尝试转换为数值类型
                            try:
                                value = float(value) if '.' in value else int(value)
                            except ValueError:
                                pass  # 保持字符串类型
                            
                            element_dict[key] = value
                
                full_path_info.append(element_dict)
            
            result = {
                'Source': source_uid,
                'Destination': destination_uid,
                'number of channels': infos.number_of_channels,
                'number of fiber': len(spans),
                'length of fiber (km)': sum(spans) / 1000,
                'Mean GSNR (0.1nm, dB)': convert_to_spectrum_array(
                    per_label_average(mypath[-1].snr_01nm, mypath[-1].propagated_labels),
                    'mean_GSNR_0_1nm'
                ),
                'Mean GSNR (signal bw, dB)': convert_to_spectrum_array(
                    per_label_average(mypath[-1].snr, mypath[-1].propagated_labels),
                    'mean_GSNR_signal_bw'
                ),
                'Mean OSNR ASE (0.1nm, dB)': convert_to_spectrum_array(
                    per_label_average(mypath[-1].osnr_ase_01nm, mypath[-1].propagated_labels),
                    'mean_OSNR_ASE_0_1nm'
                ),
                'Mean OSNR ASE (signal bw, dB)': convert_to_spectrum_array(
                    per_label_average(mypath[-1].osnr_ase, mypath[-1].propagated_labels),
                    'mean_OSNR_ASE_signal_bw'
                ),
                'Total CD (ps/nm)': mean(mypath[-1].chromatic_dispersion),
                'Total PMD (ps)': mean(mypath[-1].pmd),
                'Total PDL (dB)': mean(mypath[-1].pdl),
                'Total Latency (ms)': mean(mypath[-1].latency),
                'Total Actual pch out (dBm)': per_label_average(watt2dbm(mypath[-1].tx_power), mypath[-1].propagated_labels),
                'path': res_path,
                'full_path_info': full_path_info,  # 使用新的 full_path_info
                'full_channel_info': channel_data,
            }
            return result, 200
        except Exception as e:
            return {"message": "仿真失败: " + str(e)}, 500 