import copy
from collections.abc import Mapping

class TemplateMerger(Mapping):
    def __init__(self, data: dict):
        self._original_data = copy.deepcopy(data)
        self._macros = self._original_data.pop("macros", {})
        self._general = self._apply_macros(self._original_data.get("general", {}))
        self._specifics = {
            k: self._apply_macros(v)
            for k, v in self._original_data.items()
            if k != "general"
        }

    def _apply_macros(self, value):
        if isinstance(value, str):
            for k, v in self._macros.items():
                value = value.replace(f"{{{k}}}", v)
            return value
        elif isinstance(value, dict):
            return {k: self._apply_macros(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._apply_macros(v) for v in value]
        else:
            return value

    def _merge(self, specific: dict, general: dict) -> dict:        
        result = {}
        keys = set(specific.keys()) | set(general.keys())
        for key in keys:
            val_specific = specific.get(key)
            val_general = general.get(key)
            if isinstance(val_specific, dict) or isinstance(val_general, dict):
                result[key] = self._merge(val_specific or {}, val_general or {})
            else:
                result[key] = val_specific if val_specific is not None else val_general
        return result

    def __getitem__(self, key):
        if key in self._specifics:
            if not isinstance(self._specifics[key], dict):
                return self._specifics[key]
            return self._merge(self._specifics[key], self._general)
        
        return self._merge({}, self._general)

    def __iter__(self):
        return iter(list(self._specifics.keys()) + ["general"])

    def __len__(self):
        return len(self._specifics) + 1

    # Read-only protection
    def __setitem__(self, key, value): raise TypeError(f"{self.__class__.__name__} is read-only")
    def __delitem__(self, key): raise TypeError(f"{self.__class__.__name__} is read-only")
    def clear(self): raise TypeError(f"{self.__class__.__name__} is read-only")
    def pop(self, key, default=None): raise TypeError(f"{self.__class__.__name__} is read-only")
    def popitem(self): raise TypeError(f"{self.__class__.__name__} is read-only")
    def update(self, *args, **kwargs): raise TypeError(f"{self.__class__.__name__} is read-only")
