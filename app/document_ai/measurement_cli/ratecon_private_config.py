"""Command config for the private RateCon measurement CLI."""

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class PrivateRateconMeasurementCommandConfig:
    """Parsed CLI values for preflight validation.

    The config intentionally carries parsed values only. It does not touch
    private PDFs, write files, call providers, or run measurement.
    """

    values: MappingProxyType

    def __getattr__(self, name):
        try:
            return self.values[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def as_dict(self):
        """Return a plain dictionary copy of parsed command values."""
        return dict(self.values)


def build_private_ratecon_measurement_config(args):
    """Build a config wrapper from an argparse namespace."""
    return PrivateRateconMeasurementCommandConfig(
        values=MappingProxyType(dict(vars(args)))
    )
