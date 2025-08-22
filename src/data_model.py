# src/data_model.py
import json
import re
from PyQt6.QtCore import QRectF

class AnnotationData:
    def __init__(self):
        self.components = {}
        self.image_path = None
        self.skipped_reason = None

    # --- NO CHANGES to clear, load_from_json, save_to_json, add_component ---
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
                    for comp_details in data.values():
                        for conn_list in comp_details.get('connections', {}).values():
                            for conn in conn_list:
                                if 'count' not in conn:
                                    conn['count'] = 1
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
            return
            
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

    # --- MODIFICATION: Simplified remove_component ---
    def remove_component(self, name):
        if name in self.components:
            del self.components[name]
            # Now we only need to clean up connections TO the deleted component
            for comp_name, details in self.components.items():
                for conn_type in ["input", "output", "inout"]:
                    details["connections"][conn_type] = [
                        conn for conn in details["connections"][conn_type] if conn["name"] != name
                    ]

    # --- NO CHANGE to rename_component ---
    def rename_component(self, old_name, new_name):
        if new_name in self.components:
            raise ValueError(f"Component name '{new_name}' already exists.")
        if old_name not in self.components:
            return

        self.components[new_name] = self.components.pop(old_name)

        for details in self.components.values():
            for conn_list in details["connections"].values():
                for conn in conn_list:
                    if conn["name"] == old_name:
                        conn["name"] = new_name
    
    # --- MODIFICATION: Simplified update_connections_from_string ---
    def update_connections_from_string(self, comp_name, conn_type, conn_str):
        if comp_name not in self.components: return

        new_conns = []
        conn_parts = [p.strip() for p in conn_str.split(',') if p.strip()]
        for part in conn_parts:
            match = re.match(r'(.+?)\s*\*+\s*([0-9]+)', part)
            if match:
                name, count = match.groups()
                new_conns.append({'name': name.strip(), 'count': int(count)})
            else:
                new_conns.append({'name': part, 'count': 1})
        
        old_conns = self.components[comp_name]['connections'][conn_type]
        
        # Reciprocity now only applies to 'inout' type connections
        reciprocal_type = {'inout': 'inout'}.get(conn_type)
        
        if reciprocal_type:
            # Remove old reciprocal connections
            for old_conn in old_conns:
                target_name = old_conn['name']
                if target_name in self.components:
                    self.components[target_name]['connections'][reciprocal_type] = [
                        c for c in self.components[target_name]['connections'][reciprocal_type] if c['name'] != comp_name
                    ]

        # Set the new connections for the source component
        self.components[comp_name]['connections'][conn_type] = new_conns
        
        if reciprocal_type:
            # Add new reciprocal connections
            for new_conn in new_conns:
                target_name = new_conn['name']
                if target_name in self.components and target_name != comp_name:
                    if not any(c['name'] == comp_name for c in self.components[target_name]['connections'][reciprocal_type]):
                         self.components[target_name]['connections'][reciprocal_type].append({'name': comp_name, 'count': 1})

    # --- MODIFICATION: Simplified add_connection ---
    def add_connection(self, source_name, target_name, conn_type):
        if source_name not in self.components or target_name not in self.components:
            return

        def _update_or_add(conn_list, name_to_add):
            existing_conn = next((c for c in conn_list if c['name'] == name_to_add), None)
            if existing_conn:
                existing_conn['count'] = existing_conn.get('count', 1) + 1
            else:
                conn_list.append({"name": name_to_add, "count": 1})

        if conn_type == 'output':
            # ONLY add to the source's output list
            _update_or_add(self.components[source_name]['connections']['output'], target_name)
        
        elif conn_type == 'inout':
            # inout remains reciprocal
            _update_or_add(self.components[source_name]['connections']['inout'], target_name)
            _update_or_add(self.components[target_name]['connections']['inout'], source_name)

    # --- MODIFICATION: Simplified remove_connection ---
    def remove_connection(self, source_name, target_name, conn_type):
        if source_name not in self.components or target_name not in self.components:
            return

        def _decrement_or_remove(conn_list, name_to_remove):
            conn_to_modify = next((c for c in conn_list if c['name'] == name_to_remove), None)
            if conn_to_modify:
                if conn_to_modify.get('count', 1) > 1:
                    conn_to_modify['count'] -= 1
                else:
                    conn_list[:] = [c for c in conn_list if c['name'] != name_to_remove]

        if conn_type == 'output':
            # ONLY remove from the source's output list
            _decrement_or_remove(self.components[source_name]['connections']['output'], target_name)
        elif conn_type == 'inout':
            # inout remains reciprocal
            _decrement_or_remove(self.components[source_name]['connections']['inout'], target_name)
            _decrement_or_remove(self.components[target_name]['connections']['inout'], source_name)

    # --- REMOVED: get_non_reciprocal_connections is no longer needed ---
    # The entire method has been deleted.