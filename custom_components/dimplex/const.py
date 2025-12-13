"""Constants for the Dimplex integration."""

from enum import StrEnum
from typing import Final

DOMAIN = "dimplex"

# Default configuration
DEFAULT_NAME = "Dimplex"
DEFAULT_PORT = 502  # Modbus TCP standard port

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_NAME = "name"
CONF_MODEL = "model"

# Options keys (user-configurable features)
OPT_COOLING_ENABLED = "cooling_enabled"
OPT_DHW_ENABLED = "dhw_enabled"
OPT_POOL_ENABLED = "pool_enabled"
OPT_SECOND_HEATING_CIRCUIT = "second_heating_circuit"

# Write protection
ATTR_WRITE_ENABLED = "write_enabled"


class HeatPumpModel(StrEnum):
    """Dimplex heat pump model series."""

    LA1422C = "la1422c"
    LA_SERIES = "la_series"
    LI_SERIES = "li_series"
    SI_SERIES = "si_series"
    SIK_SERIES = "sik_series"
    WI_SERIES = "wi_series"
    GENERIC = "generic"


# Model display names
MODEL_NAMES: Final[dict[str, str]] = {
    HeatPumpModel.LA1422C: "LA 1422C (Air/Water)",
    HeatPumpModel.LA_SERIES: "LA Series (Air/Water)",
    HeatPumpModel.LI_SERIES: "LI Series (Air/Water Split)",
    HeatPumpModel.SI_SERIES: "SI/SIH Series (Brine/Water)",
    HeatPumpModel.SIK_SERIES: "SIK Series (Reversible Brine/Water)",
    HeatPumpModel.WI_SERIES: "WI Series (Water/Water)",
    HeatPumpModel.GENERIC: "Generic Dimplex Heat Pump",
}


# Model capabilities - defines what features each model supports
# "available" = hardware capability, user can enable/disable via options
# True = always available, False = not available, "optional" = user choice
MODEL_CAPABILITIES: Final[dict[str, dict[str, bool | str]]] = {
    HeatPumpModel.LA1422C: {
        "cooling_capable": True,  # Hardware supports cooling
        "cooling_default": False,  # But typically not installed
        "passive_cooling": False,  # No passive cooling (air source)
        "dhw_capable": True,
        "dhw_default": True,
        "pool_capable": True,
        "pool_default": False,
        "second_hc_capable": True,
        "second_hc_default": False,
        "defrost": True,  # Air source needs defrost
        "brine_circuit": False,
        "max_heating_power_kw": 22,
        "min_heating_power_kw": 14,
        "heat_source": "air",
    },
    HeatPumpModel.LA_SERIES: {
        "cooling_capable": True,
        "cooling_default": False,
        "passive_cooling": False,
        "dhw_capable": True,
        "dhw_default": True,
        "pool_capable": True,
        "pool_default": False,
        "second_hc_capable": True,
        "second_hc_default": False,
        "defrost": True,
        "brine_circuit": False,
        "heat_source": "air",
    },
    HeatPumpModel.LI_SERIES: {
        "cooling_capable": True,
        "cooling_default": False,
        "passive_cooling": False,
        "dhw_capable": True,
        "dhw_default": True,
        "pool_capable": True,
        "pool_default": False,
        "second_hc_capable": True,
        "second_hc_default": False,
        "defrost": True,
        "brine_circuit": False,
        "heat_source": "air",
    },
    HeatPumpModel.SI_SERIES: {
        "cooling_capable": True,
        "cooling_default": False,
        "passive_cooling": True,  # Ground source can do passive cooling
        "dhw_capable": True,
        "dhw_default": True,
        "pool_capable": True,
        "pool_default": False,
        "second_hc_capable": True,
        "second_hc_default": False,
        "defrost": False,  # Ground source doesn't need defrost
        "brine_circuit": True,
        "heat_source": "brine",
    },
    HeatPumpModel.SIK_SERIES: {
        "cooling_capable": True,
        "cooling_default": True,  # Reversible - cooling is primary feature
        "passive_cooling": True,
        "dhw_capable": True,
        "dhw_default": True,
        "pool_capable": True,
        "pool_default": False,
        "second_hc_capable": True,
        "second_hc_default": False,
        "defrost": False,
        "brine_circuit": True,
        "heat_source": "brine",
    },
    HeatPumpModel.WI_SERIES: {
        "cooling_capable": True,
        "cooling_default": False,
        "passive_cooling": True,
        "dhw_capable": True,
        "dhw_default": True,
        "pool_capable": True,
        "pool_default": False,
        "second_hc_capable": True,
        "second_hc_default": False,
        "defrost": False,
        "brine_circuit": False,
        "heat_source": "water",
    },
    HeatPumpModel.GENERIC: {
        "cooling_capable": True,
        "cooling_default": False,
        "passive_cooling": False,
        "dhw_capable": True,
        "dhw_default": True,
        "pool_capable": True,
        "pool_default": False,
        "second_hc_capable": True,
        "second_hc_default": False,
        "defrost": True,
        "brine_circuit": False,
        "heat_source": "unknown",
    },
}


def get_model_capabilities(model: str) -> dict[str, bool | str]:
    """Get capabilities for a specific model.
    
    Args:
        model: The heat pump model identifier
        
    Returns:
        Dictionary of capabilities for the model
    """
    return MODEL_CAPABILITIES.get(model, MODEL_CAPABILITIES[HeatPumpModel.GENERIC])

