# src/data_model.py
import json
import re
from PyQt6.QtCore import QRectF

class AnnotationData:
    def __init__(self):
        self.components = {}
        self.image_path = None
        self.skipped_reason = None

    def clear(self):
        self.components.clear()
        self.image_path = None
        self.skipped_reason = None

    def load_from_json(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "status" in data and data["status"] == "skipped":
                    self.skipped_reason = data.get("reason", "Unknown")
                    self.components = {}
                else:
                    self.components = data
                    self.skipped_reason = None
            return True
        except (FileNotFoundError, json.JSONDecodeError):
            self.components = {}
            self.skipped_reason = None
            return False

    def save_to_json(self, file_path):
        if self.skipped_reason:
            data_to_save = {"status": "skipped", "reason": self.skipped_reason}
        elif self.components:
            data_to_save = self.components
        else:
            return # Don't save empty files unless skipped
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Error saving JSON: {e}")
            return False

    def add_component(self, name, box: QRectF):
        if name in self.components:
            raise ValueError(f"Component with name '{name}' already exists.")
        
        self.components[name] = {
            "component_box": [box.x(), box.y(), box.x() + box.width(), box.y() + box.height()],
            "connections": {"input": [], "output": [], "inout": []}
        }

    def remove_component(self, name):
        if name in self.components:
            del self.components[name]
            # Also remove all connections pointing to the deleted component
            for comp_name, details in self.components.items():
                for conn_type in ["input", "output", "inout"]:
                    details["connections"][conn_type] = [
                        conn for conn in details["connections"][conn_type] if conn["name"] != name
                    ]

    def rename_component(self, old_name, new_name):
        if new_name in self.components:
            raise ValueError(f"Component name '{new_name}' already exists.")
        if old_name not in self.components:
            return

        # Rename the component key
        self.components[new_name] = self.components.pop(old_name)

        # Update all references to this component
        for details in self.components.values():
            for conn_list in details["connections"].values():
                for conn in conn_list:
                    if conn["name"] == old_name:
                        conn["name"] = new_name
    
    def update_connections_from_string(self, comp_name, conn_type, conn_str):
        if comp_name not in self.components: return

        # Parse the string: "compA, compB*3, compC"
        new_conns = []
        conn_parts = [p.strip() for p in conn_str.split(',') if p.strip()]
        for part in conn_parts:
            match = re.match(r'(.+?)\s*\*+\s*([0-9]+)', part)
            if match:
                name, count = match.groups()
                new_conns.append({'name': name.strip(), 'count': int(count)})
            else:
                new_conns.append({'name': part, 'count': 1})
        
        # Before updating, find the reciprocal connections and remove them
        # E.g., if we are updating comp_name's "output", we need to remove comp_name from the "input" of its old targets.
        old_conns = self.components[comp_name]['connections'][conn_type]
        reciprocal_type = {'output': 'input', 'input': 'output', 'inout': 'inout'}.get(conn_type)
        
        if reciprocal_type:
            for old_conn in old_conns:
                target_name = old_conn['name']
                if target_name in self.components:
                    self.components[target_name]['connections'][reciprocal_type] = [
                        c for c in self.components[target_name]['connections'][reciprocal_type] if c['name'] != comp_name
                    ]

        # Set the new connections for the source component
        self.components[comp_name]['connections'][conn_type] = new_conns
        
        # Add the new reciprocal connections
        if reciprocal_type:
            for new_conn in new_conns:
                target_name = new_conn['name']
                if target_name in self.components and target_name != comp_name:
                    # Avoid duplicates
                    if not any(c['name'] == comp_name for c in self.components[target_name]['connections'][reciprocal_type]):
                         self.components[target_name]['connections'][reciprocal_type].append({'name': comp_name, 'count': 1})


    def add_connection(self, source_name, target_name, conn_type):
        if source_name not in self.components or target_name not in self.components:
            return

        if conn_type == 'output':
            # Add to source's output
            if not any(conn['name'] == target_name for conn in self.components[source_name]['connections']['output']):
                self.components[source_name]['connections']['output'].append({"name": target_name, "count": 1})
            # Add to target's input
            if not any(conn['name'] == source_name for conn in self.components[target_name]['connections']['input']):
                self.components[target_name]['connections']['input'].append({"name": source_name, "count": 1})
        
        elif conn_type == 'inout':
            # Add to both inout lists
            if not any(conn['name'] == target_name for conn in self.components[source_name]['connections']['inout']):
                self.components[source_name]['connections']['inout'].append({"name": target_name, "count": 1})
            if not any(conn['name'] == source_name for conn in self.components[target_name]['connections']['inout']):
                 self.components[target_name]['connections']['inout'].append({"name": source_name, "count": 1})

    def remove_connection(self, source_name, target_name, conn_type):
        if source_name not in self.components or target_name not in self.components:
            return

        def remove_from_list(comp_list, name_to_remove):
            return [conn for conn in comp_list if conn['name'] != name_to_remove]

        if conn_type == 'output':
            self.components[source_name]['connections']['output'] = remove_from_list(
                self.components[source_name]['connections']['output'], target_name)
            self.components[target_name]['connections']['input'] = remove_from_list(
                self.components[target_name]['connections']['input'], source_name)
        elif conn_type == 'inout':
            self.components[source_name]['connections']['inout'] = remove_from_list(
                self.components[source_name]['connections']['inout'], target_name)
            self.components[target_name]['connections']['inout'] = remove_from_list(
                self.components[target_name]['connections']['inout'], source_name)