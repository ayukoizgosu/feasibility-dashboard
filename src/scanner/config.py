"""Configuration loader for Site Scanner."""

from pathlib import Path
from typing import Any
import os

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class GeocodingConfig(BaseModel):
    """Geocoding settings."""
    provider: str = "google"
    daily_limit: int = 1000
    monthly_limit: int = 40000


class FiltersConfig(BaseModel):
    """Listing filter settings."""
    property_types: list[str] = ["house", "vacant_land"]
    price_max: int = 2000000
    land_size_min_m2: int = 400
    exclude_keywords: list[str] = ["apartment", "unit", "townhouse", "villa"]


class FeasibilityConfig(BaseModel):
    """Feasibility calculation settings."""
    build_cost_per_m2: float = 2800
    soft_cost_pct: float = 0.15
    contingency_pct: float = 0.10
    holding_months: int = 18
    finance_rate: float = 0.075
    selling_cost_pct: float = 0.04
    avg_dwelling_size_m2: float = 180


class ZoneParams(BaseModel):
    """Zone-specific development parameters."""
    site_coverage_max: float = 0.60
    garden_area_min: float | None = None
    height_limit_m: float | None = None
    max_dwellings: int | None = None
    yield_factor: float = 0.002  # dwellings per m2 land


class OutputConfig(BaseModel):
    """Output settings."""
    top_n: int = 25
    reports_dir: str = "reports"


class Settings(BaseSettings):
    """Environment-based settings."""
    google_maps_api_key: str = ""
    domain_client_id: str = ""
    domain_client_secret: str = ""
    top_n: int = 25
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class Config:
    """Main configuration class combining YAML and env settings."""
    
    def __init__(self, config_path: str | Path | None = None):
        self.settings = Settings()
        
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"
        
        self.config_path = Path(config_path)
        self._raw: dict[str, Any] = {}
        self._load_yaml()
        
        # Parse into typed configs
        self.suburbs: list[str] = self._raw.get("suburbs", [])
        self.filters = FiltersConfig(**self._raw.get("filters", {}))
        self.geocoding = GeocodingConfig(**self._raw.get("geocoding", {}))
        self.feasibility = FeasibilityConfig(**self._raw.get("feasibility", {}))
        self.output = OutputConfig(**self._raw.get("output", {}))
        
        # Zone parameters
        self.zones: dict[str, ZoneParams] = {}
        for zone_code, params in self._raw.get("zones", {}).items():
            self.zones[zone_code] = ZoneParams(**params)
        
        # Constraint severities
        self.constraints: dict[str, int] = self._raw.get("constraints", {})
    
    def _load_yaml(self) -> None:
        """Load YAML configuration file."""
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._raw = yaml.safe_load(f) or {}
        else:
            self._raw = {}
    
    @property
    def google_api_key(self) -> str:
        """Get Google Maps API key."""
        return self.settings.google_maps_api_key
    
    def get_zone_params(self, zone_code: str) -> ZoneParams:
        """Get parameters for a zone, with fallback to defaults."""
        # Try exact match first
        if zone_code in self.zones:
            return self.zones[zone_code]
        
        # Try base zone (e.g., GRZ1 -> GRZ)
        base_zone = "".join(c for c in zone_code if not c.isdigit())
        for key in self.zones:
            if key.startswith(base_zone):
                return self.zones[key]
        
        # Return default
        return ZoneParams()
    
    def get_constraint_severity(self, overlay_code: str) -> int:
        """Get severity for an overlay code."""
        # Try exact match
        if overlay_code in self.constraints:
            return self.constraints[overlay_code]
        
        # Try base code (e.g., HO123 -> HO)
        base_code = "".join(c for c in overlay_code if not c.isdigit())
        return self.constraints.get(base_code, 0)


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get or create global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
