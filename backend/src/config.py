import collections.abc
import json
from pathlib import Path


def deep_update(d, u):
    """
    Deeply update elements of nested dict d with update u
    """

    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = deep_update(d.get(k, {}), v)
        else:
            d[k] = v

    return d


class Config:
    def deep_update(self, settings):
        """
        Deeply update elements of nested self.__dict__ with update u
        """

        d = self.__dict__

        for k, v in d.items():
            if isinstance(v, Config):
                d[k].deep_update(settings.get(k, {}))
            elif isinstance(v, collections.abc.Mapping):
                d[k] = deep_update(v, settings.get(k, {}))
            else:
                d[k] = settings.get(k, v)

        return d

    def deep_update_with_json_config(self, config_filename: Path):
        with open(config_filename) as f:
            provided_config = json.load(f)
        self.deep_update(provided_config)

    def to_dict(self):
        res = {}

        for k, v in self.__dict__.items():
            if isinstance(v, Config):
                res[k] = v.to_dict()
            else:
                res[k] = v

        return res
