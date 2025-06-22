# app/common/user_yaml_manager.py

from ruamel.yaml import YAML

class YamlManager:
    def __init__(self, path):
        self.path = path
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.allow_unicode = True
        self.yaml.indent(sequence=4, offset=2)
        self.yaml.width = 4096

    def load(self):
        try:
            with self.path.open('r', encoding='utf-8') as f:
                return self.yaml.load(f), None
        except Exception as e:
            return None, str(e)

    def dump(self, data):
        try:
            with self.path.open('w', encoding='utf-8') as f:
                self.yaml.dump(data, f)
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def extract_keys(d):
        if isinstance(d, dict):
            return {k: YamlManager.extract_keys(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [YamlManager.extract_keys(v) for v in d]
        return None

    @staticmethod
    def find_key_changes(a, b, path=""):
        changes = []
        if isinstance(a, dict) and isinstance(b, dict):
            keys_a = set(a.keys())
            keys_b = set(b.keys())
            for k in keys_a - keys_b:
                changes.append(f"Removed key: {path + '.' if path else ''}{k}")
            for k in keys_b - keys_a:
                changes.append(f"Added key: {path + '.' if path else ''}{k}")
            for k in keys_a & keys_b:
                changes.extend(YamlManager.find_key_changes(a[k], b[k], f"{path + '.' if path else ''}{k}"))
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                changes.append(f"Changed list length at: {path} ({len(a)} -> {len(b)})")
            for i, (item_a, item_b) in enumerate(zip(a, b)):
                changes.extend(YamlManager.find_key_changes(item_a, item_b, f"{path}[{i}]") )
        return changes

    @staticmethod
    def update_values_only(orig, new):
        if isinstance(orig, dict) and isinstance(new, dict):
            for k in orig:
                if k in new:
                    updated_value = YamlManager.update_values_only(orig[k], new[k])
                    if updated_value is not None:
                        orig[k] = updated_value
        elif isinstance(orig, list) and isinstance(new, list):
            for i in range(min(len(orig), len(new))):
                updated_value = YamlManager.update_values_only(orig[i], new[i])
                if updated_value is not None:
                    orig[i] = updated_value
        else:
            return new

    def check_key_structure(self, orig, new):
        a = self.extract_keys(orig)
        b = self.extract_keys(new)
        if a != b:
            changes = self.find_key_changes(a, b)
            return False, changes
        return True, None
