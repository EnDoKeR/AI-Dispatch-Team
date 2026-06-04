from app import deprecated_mod
from app import experimental_mod
from app import side_effect_module


VALUE = "fixture-active"


def combined():
    return [VALUE, deprecated_mod.VALUE, experimental_mod.VALUE, side_effect_module.VALUE]
