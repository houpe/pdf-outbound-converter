from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


class TemplateStrategy(ABC):
    key: str
    warehouse_code: str
    validate_split_codes: bool = False

    @abstractmethod
    def parse(self, path: str, filename: str = "") -> Tuple[Dict[str, str], List[Dict[str, str]]]:
        ...

    def route_quantity(self, quantity, item_code: str, split_map: Dict[str, str]) -> Tuple[Any, Any]:
        return ("", quantity)

    def validate_items(self, items: List[Dict[str, str]], split_map: Dict[str, str]) -> None:
        pass


STRATEGY_REGISTRY: Dict[str, TemplateStrategy] = {}


def register_strategy(cls):
    instance = cls()
    STRATEGY_REGISTRY[cls.key] = instance
    return cls


def get_strategy(template_key: str) -> TemplateStrategy:
    if template_key not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown template: {template_key}")
    return STRATEGY_REGISTRY[template_key]


from strategies.qzz import QzzStrategy
from strategies.lmt import LmtStrategy
from strategies.hlmc import HlmcStrategy
from strategies.yss import YssStrategy
from strategies.hls import HlsStrategy
from strategies.bw import BwStrategy
from strategies.pl import PlStrategy
