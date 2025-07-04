# src/data_model.py
import json
from PyQt6.QtCore import QRectF

class AnnotationData:
    """管理单个图像的标注数据"""
    def __init__(self):
        self.components = {}
        self.image_path = None

    def clear(self):
        """清空所有数据"""
        self.components.clear()
        self.image_path = None

    def load_from_json(self, file_path):
        """从JSON文件加载数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.components = data
            return True
        except (FileNotFoundError, json.JSONDecodeError):
            self.components = {}
            return False

    def save_to_json(self, file_path):
        """将数据保存到JSON文件"""
        if not self.components:
            return
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.components, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Error saving JSON: {e}")
            return False

    def add_component(self, name, box: QRectF):
        """添加一个新组件"""
        if name in self.components:
            raise ValueError(f"Component with name '{name}' already exists.")
        
        self.components[name] = {
            "type": "",
            "component_box": [box.x(), box.y(), box.x() + box.width(), box.y() + box.height()],
            "connections": {
                "input": [],
                "output": [],
                "inout": []
            }
        }

    def remove_component(self, name):
        """删除一个组件及其所有相关连接"""
        if name in self.components:
            del self.components[name]
            for comp_name, details in self.components.items():
                for conn_type in ["input", "output", "inout"]:
                    details["connections"][conn_type] = [
                        conn for conn in details["connections"][conn_type] if conn["name"] != name
                    ]

    def add_connection(self, source_name, target_name, conn_type):
        """添加连接关系"""
        if source_name not in self.components or target_name not in self.components:
            return

        if conn_type == 'output':
            if not any(conn['name'] == target_name for conn in self.components[source_name]['connections']['output']):
                self.components[source_name]['connections']['output'].append({"name": target_name})
            if not any(conn['name'] == source_name for conn in self.components[target_name]['connections']['input']):
                self.components[target_name]['connections']['input'].append({"name": source_name})
        
        elif conn_type == 'inout':
            if not any(conn['name'] == target_name for conn in self.components[source_name]['connections']['inout']):
                self.components[source_name]['connections']['inout'].append({"name": target_name})
            if not any(conn['name'] == source_name for conn in self.components[target_name]['connections']['inout']):
                 self.components[target_name]['connections']['inout'].append({"name": source_name})

    def remove_connection(self, source_name, target_name, conn_type):
        """删除一个连接"""
        if source_name not in self.components or target_name not in self.components:
            return

        def remove_from_list(comp_list, name_to_remove):
            return [conn for conn in comp_list if conn['name'] != name_to_remove]

        if conn_type == 'output':
            # Remove from source's output and target's input
            self.components[source_name]['connections']['output'] = remove_from_list(
                self.components[source_name]['connections']['output'], target_name)
            self.components[target_name]['connections']['input'] = remove_from_list(
                self.components[target_name]['connections']['input'], source_name)
        elif conn_type == 'inout':
            # Remove from both inout lists
            self.components[source_name]['connections']['inout'] = remove_from_list(
                self.components[source_name]['connections']['inout'], target_name)
            self.components[target_name]['connections']['inout'] = remove_from_list(
                self.components[target_name]['connections']['inout'], source_name)


    def get_component_at(self, pos):
        """根据坐标获取组件名称"""
        for name, details in self.components.items():
            box = QRectF(details['component_box'][0], details['component_box'][1],
                         details['component_box'][2] - details['component_box'][0],
                         details['component_box'][3] - details['component_box'][1])
            if box.contains(pos):
                return name
        return None