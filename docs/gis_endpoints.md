# Victorian GIS Data Sources for Property Development Assessment

This document catalogs public GIS endpoints useful for automated property development impact assessment.

## Summary Table

| Category | Source | Format | Key Layers |
|----------|--------|--------|------------|
| **Sewer/Water** | Melbourne Water | ArcGIS REST | Sewerage_Network_Mains, Water_Supply_Main_Pipelines |
| **Sewer (Retail)** | Yarra Valley Water | WFS | SEWERPIPES, SEWERBRANCHES |
| **Planning** | Vicmap | WFS | Planning zones, overlays |
| **Transmission Lines** | Geoscience Australia | WFS | Electricity transmission lines |
| **Power Stations** | Digital Atlas / GA | WFS | Major power generating stations |
| **Substations** | Digital Atlas / GA | WFS | Transmission substations |
| **Pollutant Inventory** | Digital Atlas / NPI | WFS | 4000+ industrial facilities |
| **Earthquake Hazard** | Digital Atlas / GA | WFS | National Seismic Hazard Assessment |
| **Bushfire** | Data.Vic | WFS | Designated Bushfire Prone Area |
| **Contamination** | EPA Victoria | WFS | Priority Sites, Audit sites |
| **Heritage** | Heritage Victoria | WFS | Victorian Heritage Register |
| **Flood** | Data.Vic / Melbourne Water | WFS/ArcGIS | Flood history, inundation |
| **Property** | Vicmap | WFS | Parcel boundaries, easements |
| **Landfills** | EPA Victoria | WFS | Current and historical landfill sites |
| **Surface Hydrology** | Geoscience Australia | WFS | Streams, catchments |

---

## 1. Melbourne Water (Sewer & Water Mains)

**Type**: ArcGIS FeatureServer (public, no API key)

### Sewerage Network Mains
```
https://services5.arcgis.com/ZSYwjtv8RKVhkXIL/arcgis/rest/services/Sewerage_Network_Mains/FeatureServer/0
```

### Water Supply Main Pipelines
```
https://services5.arcgis.com/ZSYwjtv8RKVhkXIL/arcgis/rest/services/Water_Supply_Main_Pipelines/FeatureServer/0
```

### Query Format
```
/query?where=1=1&geometry={minX},{minY},{maxX},{maxY}&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=true&f=geojson
```

**Notes**:
- Max 2000 records per request (use pagination)
- Shows trunk/transfer mains only (indicative of sewered areas)
- **Implemented**: `src/scanner/spatial/melbourne_water.py`

---

## 2. Yarra Valley Water (Reticulated Sewer)

**Type**: WFS (may require authentication or have network restrictions)

### Endpoint
```
https://webmap.yvw.com.au/YVWassets/service.svc/get
```

### Key Layers
- `SEWERPIPES` - Main sewer pipes
- `SEWERBRANCHES` - Property connections
- `SEWERSTRUCTURES` - Maintenance holes

**Notes**:
- Often times out from external networks
- Manual check via Asset Map: https://webmap.yvw.com.au/yvw_ext/
- Call YVW: 1300 304 688 for confirmation

---

## 3. Data.Vic Open Data WFS

**Base Endpoint**:
```
https://opendata.maps.vic.gov.au/geoserver/wfs
```

### Key Layers

#### Bushfire Prone Area (BPA)
```
Layer: open-data-platform:bpa_bushfire_prone_area_current
```
- Identifies areas with bushfire building requirements
- Critical for BAL (Bushfire Attack Level) assessment

#### Fire History
```
Layer: open-data-platform:fire_history
```
- Historical fire extent polygons since 1903

#### EPA Priority Sites Register
```
Layer: open-data-platform:psr_point
```
- Sites with known contamination issues

#### EPA Environmental Audit Overlay
```
Layer: open-data-platform:eao_environmental_audit_overlay
```
- Sites where environmental audit is required

#### Flood History
```
Layer: open-data-platform:flood_history_october_2022
```
- Historical flood extent polygons

### Query Format
```
?service=WFS&version=2.0.0&request=GetFeature&typeName={layer}&outputFormat=application/json&srsName=EPSG:4326&CQL_FILTER=INTERSECTS(geometry,POINT({lon} {lat}))
```

---

## 4. Vicmap (Property & Planning)

**Base Endpoint**:
```
https://services.land.vic.gov.au/catalogue/publicproxy/guest/dv_geoserver/wfs
```

### Key Layers

#### Property Parcels
```
Layer: VMPROP_PARCEL_PROPERTY
```
- Parcel boundaries
- Lot/Plan identifiers
- Easement locations

#### Planning Zones
```
Layer: VMPLAN_ZONE
```
- All planning zones (GRZ, NRZ, LDRZ, etc.)

#### Planning Overlays
```
Layer: VMPLAN_OVERLAY
```
- All planning overlays (HO, ESO, BMO, SLO, etc.)

**Notes**:
- Already integrated in site-scanner: `src/scanner/spatial/gis_clients.py`

---

## 5. Victorian Heritage Database

**Endpoint**:
```
https://services.land.vic.gov.au/catalogue/publicproxy/guest/dv_geoserver/wfs
```

### Key Layers
```
Layer: VMFEAT_HERITAGE_REGISTER
```
- Victorian Heritage Register listings
- Heritage Overlay polygons

---

## 6. Geoscience Australia (Transmission Lines)

**Endpoint**:
```
https://services.ga.gov.au/gis/services/Foundation_Electricity_Infrastructure/MapServer/WFSServer
```

### Key Layers
```
Layer: Transmission_Lines
```
- High voltage transmission line locations
- Voltage attributes

**Notes**:
- Already integrated: `src/scanner/spatial/transmission_cache.py`
- 300m buffer rule for quick-kill assessment

---

## 7. Melbourne Water Drainage

**Type**: ArcGIS FeatureServer

### Major Catchments
```
https://services3.arcgis.com/TJxZpUnYIJOvcYwE/arcgis/rest/services/Catchments_Major_Catchments_of_Melbournes_River_Basins/FeatureServer/0
```

### Drainage Assets (if available)
- Check Melbourne Water Open Data portal for additional layers

---

## Implementation Priority

### Already Implemented
1. ✅ Vicmap Planning (zones, overlays)
2. ✅ Vicmap Property (parcels)
3. ✅ Geoscience Australia (transmission lines)
4. ✅ Melbourne Water (sewer/water mains) - NEW

### High Priority (Next)
5. 🔲 Bushfire Prone Area (BPA) - Critical for BAL
6. 🔲 EPA Priority Sites Register - Contamination check
7. 🔲 Flood History/Overlays - Development constraint

### Medium Priority
8. 🔲 Heritage Register - Development constraint
9. 🔲 Environmental Audit Overlay - Due diligence

---

## Testing Endpoints

### Test Query Template
```python
import requests

# Example: Query Bushfire Prone Area at a location
url = "https://opendata.maps.vic.gov.au/geoserver/wfs"
params = {
    "service": "WFS",
    "version": "2.0.0", 
    "request": "GetFeature",
    "typeName": "open-data-platform:bpa_bushfire_prone_area_current",
    "outputFormat": "application/json",
    "srsName": "EPSG:4326",
    "CQL_FILTER": f"INTERSECTS(geom, POINT({lon} {lat}))"
}
resp = requests.get(url, params=params, timeout=30)
```

---

## 8. Digital Atlas Australia / Geoscience Australia

**Portal**: https://digital.atlas.gov.au/search (432+ collections)

**Base WFS Endpoint**:
```
https://services.ga.gov.au/gis/services/{SERVICE_NAME}/MapServer/WFSServer
```

### Power Stations (Major Generators)
```
Service: Foundation_Electricity_Infrastructure
Layer: Major_Power_Stations
```
- All major power generating facilities
- Impacts: Visual amenity, noise, potential environmental hazards

### Transmission Substations
```
Service: Foundation_Electricity_Infrastructure
Layer: Transmission_Substations
```
- High-voltage conversion/control facilities
- Impact: EMF concerns, visual amenity, Feng Shui considerations

### National Pollutant Inventory (NPI) Facilities
```
Interactive Viewer: https://digital.atlas.gov.au/apps/national-pollutant-inventory-viewer
```
- 4000+ industrial facilities reporting emissions
- Waste transfers to landfill
- Air, water, land pollutant releases
- **Critical**: Identify nearby polluters affecting property value

### National Seismic Hazard Assessment
```
Service: NSHA2018
Layers: PGA (Peak Ground Acceleration), Response Spectra
```
- Earthquake hazard mapping
- Building code requirements

### Surface Hydrology
```
Service: Surface_Hydrology
WFS: https://services.ga.gov.au/gis/services/Surface_Hydrology/MapServer/WFSServer
```
- Stream networks
- Catchment boundaries
- Flood-prone areas

---

## 9. EPA Victoria (Contamination & Waste)

**Base Endpoint**:
```
https://opendata.maps.vic.gov.au/geoserver/wfs
```

### Priority Sites Register (PSR)
```
Layer: open-data-platform:psr_point
```
- Sites with known contamination requiring cleanup
- **Critical**: Quick-kill constraint for development

### Environmental Audit Overlay (EAO)
```
Layer: open-data-platform:eao_environmental_audit_overlay
```
- Sites where audit required before development

### Landfill Sites (Current & Historical)
```
Layer: open-data-platform:landfill_current
Layer: open-data-platform:landfill_historical
```
- Active and closed landfills
- Buffer impacts on property values

### Check Your Groundwater (CYG)
```
Layer: open-data-platform:cyg_area
```
- Areas with known groundwater contamination

### Integrated Tool: Victoria Unearthed
```
Interactive Map: https://www.epa.vic.gov.au/for-community/environmental-information/victoria-unearthed
```
- Combines all EPA contamination layers
- Best for manual verification

---

## 10. Flood Risk

### Data.Vic Flood Layers
```
Base: https://opendata.maps.vic.gov.au/geoserver/wfs
Layer: open-data-platform:flood_history_october_2022
Layer: open-data-platform:lsio_land_subject_to_inundation
```
- Historical flood extents
- LSIO planning overlay areas

### Australian Flood Risk Information Portal
```
Portal: https://digital.atlas.gov.au/apps/australian-flood-risk-information-portal
```
- Study-level metadata only (not raw flood extents)
- Links to council flood studies

### Melbourne Water Flood Mapping
- Contact Melbourne Water for detailed flood studies
- LSIO/SBO overlays available via Vicmap

---

## Property Value Impact Factors (Summary)

| Factor | Layer/Source | Impact Radius | Severity |
|--------|-------------|---------------|----------|
| **Transmission Lines** | GA Electricity | 300m | HIGH |
| **Substations** | GA Electricity | 200m | MEDIUM |
| **Power Stations** | GA Electricity | 500m | HIGH |
| **NPI Facilities** | Digital Atlas NPI | 1-5km | VARIES |
| **Landfills (active)** | EPA Victoria | 1km | HIGH |
| **Landfills (closed)** | EPA Victoria | 500m | MEDIUM |
| **Priority Sites (PSR)** | EPA Victoria | On-site | CRITICAL |
| **Bushfire Prone Area** | Data.Vic BPA | On-site | HIGH |
| **Flood Zone (LSIO)** | Vicmap Planning | On-site | HIGH |
| **Heritage Overlay** | Vicmap Planning | On-site | MEDIUM |
| **Earthquake Zone** | GA NSHA | Regional | LOW |

---

## Implementation Priority (Updated)

### Already Implemented
1. ✅ Vicmap Planning (zones, overlays)
2. ✅ Vicmap Property (parcels)
3. ✅ Geoscience Australia (transmission lines)
4. ✅ Melbourne Water (sewer/water mains)

### High Priority (Next)
5. 🔲 Substations (GA Electricity) - Feng Shui quick-kill
6. 🔲 Bushfire Prone Area (BPA) - BAL assessment
7. 🔲 EPA Priority Sites Register - Contamination check
8. 🔲 NPI Facilities - Industrial neighbour check

### Medium Priority
9. 🔲 Flood Overlays (LSIO/SBO)
10. 🔲 Power Stations
11. 🔲 Landfill Sites
12. 🔲 Heritage Register

---

## References

- [Digital Atlas of Australia](https://digital.atlas.gov.au/)
- [Data.Vic Portal](https://data.vic.gov.au/)
- [Vicmap as a Service](https://www.land.vic.gov.au/maps-and-spatial/spatial-data/vicmap-as-a-service)
- [Melbourne Water Open Data](https://data.melbourne.vic.gov.au/)
- [EPA Victoria Unearthed](https://www.epa.vic.gov.au/for-community/environmental-information/victoria-unearthed)
- [VicPlan](https://mapshare.vic.gov.au/vicplan/)
- [Geoscience Australia Web Services](https://services.ga.gov.au/)
- [National Pollutant Inventory](https://www.dcceew.gov.au/environment/protection/npi)
