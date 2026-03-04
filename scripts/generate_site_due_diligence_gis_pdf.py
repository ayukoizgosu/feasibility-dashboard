from __future__ import annotations

import argparse
import io
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from shapely.geometry import Point, shape

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scanner.planning.rules import calculate_max_footprint
from scanner.spatial.data_vic_checks import (
    check_bushfire_prone_area,
    check_enviro_audit_sites,
    check_epa_priority_sites,
)
from scanner.spatial.ga_infrastructure import (
    check_power_station_proximity,
    check_substation_proximity,
)
from scanner.spatial.geometry import (
    calculate_approx_area_sqm,
    calculate_slope_and_elevation,
    get_property_polygon,
)
from scanner.spatial.gis_clients import (
    LAYER_PLANNING_OVERLAY,
    LAYER_PLANNING_ZONE,
    VICMAP_WFS_BASE,
    get_zones_at_point,
    query_wfs_features,
)


def money(v: float) -> str:
    return f"${v:,.0f}"


def expand_bbox(bounds: tuple[float, float, float, float], pad_ratio: float = 0.25) -> tuple[float, float, float, float]:
    minx, miny, maxx, maxy = bounds
    dx = max(0.0008, (maxx - minx) * pad_ratio)
    dy = max(0.0008, (maxy - miny) * pad_ratio)
    return (minx - dx, miny - dy, maxx + dx, maxy + dy)


def lonlat_to_px(lon: float, lat: float, bbox: tuple[float, float, float, float], size: tuple[int, int]) -> tuple[int, int]:
    minx, miny, maxx, maxy = bbox
    w, h = size
    x = (lon - minx) / (maxx - minx) * w
    y = (maxy - lat) / (maxy - miny) * h
    return int(x), int(y)


def fetch_aerial_image(bbox: tuple[float, float, float, float], size: tuple[int, int]) -> Image.Image:
    params = {
        "bbox": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
        "bboxSR": "4326",
        "imageSR": "4326",
        "size": f"{size[0]},{size[1]}",
        "format": "png32",
        "transparent": "false",
        "f": "image",
    }
    url = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGBA")
    except Exception:
        # Fallback if aerial tile service is unavailable from this network.
        img = Image.new("RGBA", size, (19, 33, 58, 255))
        d = ImageDraw.Draw(img, "RGBA")
        d.rectangle((16, 16, size[0] - 16, 80), fill=(30, 58, 95, 220), outline=(89, 129, 192, 220), width=2)
        d.text((28, 38), "Aerial basemap unavailable (network timeout). Overlay geometry still shown.", fill=(235, 245, 255, 255))
        return img


def draw_geometry(draw: ImageDraw.ImageDraw, geom: Any, bbox: tuple[float, float, float, float], size: tuple[int, int], line: tuple[int, int, int, int], fill: tuple[int, int, int, int] | None = None, width: int = 2) -> None:
    gtype = geom.geom_type
    if gtype == "Polygon":
        exterior = [lonlat_to_px(x, y, bbox, size) for x, y in geom.exterior.coords]
        if fill:
            draw.polygon(exterior, fill=fill, outline=line)
        else:
            draw.line(exterior + [exterior[0]], fill=line, width=width)
    elif gtype == "MultiPolygon":
        for p in geom.geoms:
            draw_geometry(draw, p, bbox, size, line=line, fill=fill, width=width)
    elif gtype == "LineString":
        pts = [lonlat_to_px(x, y, bbox, size) for x, y in geom.coords]
        draw.line(pts, fill=line, width=width)
    elif gtype == "MultiLineString":
        for ls in geom.geoms:
            draw_geometry(draw, ls, bbox, size, line=line, fill=fill, width=width)
    elif gtype == "Point":
        x, y = lonlat_to_px(geom.x, geom.y, bbox, size)
        r = 4
        draw.ellipse((x - r, y - r, x + r, y + r), fill=line, outline=(255, 255, 255, 255))


def overlay_intersections(parcel_geom: Any, layer: str, bbox: tuple[float, float, float, float]) -> list[dict[str, Any]]:
    feats = query_wfs_features(VICMAP_WFS_BASE, layer, bbox=bbox, max_features=600)
    found: list[dict[str, Any]] = []
    for f in feats:
        try:
            g = shape(f.get("geometry", {}))
            if not g.is_valid:
                g = g.buffer(0)
            if g.intersects(parcel_geom):
                found.append(f)
        except Exception:
            continue
    return found


def estimate_slope_cost_uplift(slope_pct: float) -> tuple[float, str]:
    if slope_pct <= 5:
        return 0.00, "Flat site: standard earthworks profile."
    if slope_pct <= 10:
        return 0.05, "Moderate slope: retaining and drainage uplift likely."
    if slope_pct <= 15:
        return 0.10, "Steeper site: significant retaining, cut/fill and access impacts."
    return 0.20, "High slope risk: specialist engineering and reduced yield likely."


def build_report(args: argparse.Namespace) -> Path:
    address = args.address
    lat = float(args.lat)
    lon = float(args.lon)
    out_dir = ROOT_DIR / "examples"
    out_dir.mkdir(parents=True, exist_ok=True)

    parcel = get_property_polygon(lat, lon)
    if parcel is None:
        raise RuntimeError("No parcel polygon found at this location.")

    parcel_area = calculate_approx_area_sqm(parcel)
    slope_pct, elev_m, slope_note = calculate_slope_and_elevation(parcel)
    uplift, uplift_note = estimate_slope_cost_uplift(slope_pct)

    zones = get_zones_at_point(lat, lon)
    zone_code = zones[0].get("code") if zones else "GRZ1"
    max_footprint, footprint_notes = calculate_max_footprint(parcel_area, zone_code)

    bbox = expand_bbox(parcel.bounds, pad_ratio=0.5)
    size = (1200, 800)
    aerial = fetch_aerial_image(bbox, size)
    draw = ImageDraw.Draw(aerial, "RGBA")

    zone_hits = overlay_intersections(parcel, LAYER_PLANNING_ZONE, bbox)
    overlay_hits = overlay_intersections(parcel, LAYER_PLANNING_OVERLAY, bbox)

    # Draw nearby planning polygons lightly and parcel strongly.
    for f in zone_hits[:20]:
        try:
            draw_geometry(draw, shape(f["geometry"]), bbox, size, line=(39, 174, 96, 200), fill=(39, 174, 96, 45), width=2)
        except Exception:
            continue
    for f in overlay_hits[:40]:
        try:
            draw_geometry(draw, shape(f["geometry"]), bbox, size, line=(239, 68, 68, 220), fill=(239, 68, 68, 35), width=2)
        except Exception:
            continue
    draw_geometry(draw, parcel, bbox, size, line=(59, 130, 246, 255), fill=(59, 130, 246, 45), width=3)
    draw_geometry(draw, Point(lon, lat), bbox, size, line=(255, 255, 0, 255), fill=None, width=2)

    map_path = out_dir / "site_due_diligence_map.png"
    aerial.save(map_path)

    # Environmental + infrastructure checks
    bpa, _ = check_bushfire_prone_area(lat, lon)
    epa = check_epa_priority_sites(lat, lon, radius_m=1000)
    audit = check_enviro_audit_sites(lat, lon, radius_m=1000)
    near_sub, sub_dist, _ = check_substation_proximity(lat, lon, radius_m=500)
    near_ps, ps_dist, _ = check_power_station_proximity(lat, lon, radius_m=1000)

    # Basic build-cost estimate example
    build_rate = args.base_build_rate
    base_construction = build_rate * max_footprint
    uplift_cost = base_construction * uplift
    adjusted_construction = base_construction + uplift_cost

    pdf_path = out_dir / "site_due_diligence_gis_report.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"GIS Due Diligence - {address}",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="H1", parent=styles["Heading1"], fontSize=16, leading=20))
    styles.add(ParagraphStyle(name="H2", parent=styles["Heading2"], fontSize=11.5, leading=14))
    styles.add(ParagraphStyle(name="BodyTight", parent=styles["BodyText"], fontSize=9.3, leading=12.5))
    story = []

    story.append(Paragraph("Comprehensive Site Due Diligence Report", styles["H1"]))
    story.append(Paragraph(f"Address: {address}", styles["BodyText"]))
    story.append(Paragraph(f"Coordinates: {lat:.6f}, {lon:.6f}", styles["BodyText"]))
    story.append(Paragraph(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", styles["BodyText"]))
    story.append(Spacer(1, 7))

    story.append(Paragraph("1. GIS Aerial View with Zoning/Overlay Context", styles["H2"]))
    story.append(Paragraph(
        "Blue polygon = parcel; green = intersecting planning zone polygon(s); red = intersecting planning overlay polygon(s).",
        styles["BodyTight"],
    ))
    story.append(Spacer(1, 4))
    story.append(RLImage(str(map_path), width=175 * mm, height=115 * mm))
    story.append(Spacer(1, 8))

    story.append(Paragraph("2. Planning Controls and Overlay Summary", styles["H2"]))
    overlay_codes = []
    for f in overlay_hits:
        p = f.get("properties", {})
        code = p.get("ZONE_CODE") or p.get("ZONE") or p.get("LABEL") or p.get("MAP_LAB")
        if code:
            overlay_codes.append(str(code))
    zone_codes = []
    for f in zone_hits:
        p = f.get("properties", {})
        code = p.get("ZONE_CODE") or p.get("ZONE") or p.get("LABEL")
        if code:
            zone_codes.append(str(code))

    planning_tbl = Table(
        [
            ["Primary Zone", zone_code],
            ["Intersecting Zone Features", ", ".join(sorted(set(zone_codes))) or "None detected in bbox query"],
            ["Intersecting Overlay Features", ", ".join(sorted(set(overlay_codes))) or "None detected in bbox query"],
            ["Parcel Area (approx.)", f"{parcel_area:,.0f} m²"],
        ],
        colWidths=[60 * mm, 120 * mm],
    )
    planning_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2FF")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(planning_tbl)
    story.append(Spacer(1, 8))

    story.append(Paragraph("3. Environmental and Infrastructure Constraints", styles["H2"]))
    env_tbl = Table(
        [
            ["Bushfire Prone Area", "Yes" if bpa else "No / not detected"],
            ["EPA Priority Sites (1km)", str(len(epa))],
            ["Environmental Audit Sites (1km)", str(len(audit))],
            ["Transmission Substation (500m)", f"Yes (~{sub_dist:.0f}m)" if near_sub and sub_dist else "No / not detected"],
            ["Major Power Station (1km)", f"Yes (~{ps_dist:.0f}m)" if near_ps and ps_dist else "No / not detected"],
        ],
        colWidths=[80 * mm, 100 * mm],
    )
    env_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(env_tbl)
    story.append(Spacer(1, 8))

    story.append(Paragraph("4. Topography, Buildable Footprint and Cost Impact", styles["H2"]))
    topo_tbl = Table(
        [
            ["Average Elevation", f"{elev_m:.1f} m"],
            ["Estimated Slope", f"{slope_pct:.2f}% ({slope_note})"],
            ["Max Buildable Footprint", f"{max_footprint:,.0f} m²"],
            ["Footprint Rule Notes", "; ".join(footprint_notes)],
            ["Baseline Construction (@rate)", f"{money(base_construction)} ({money(build_rate)}/m²)"],
            ["Slope Uplift", f"{uplift*100:.0f}% -> {money(uplift_cost)}"],
            ["Adjusted Construction Estimate", money(adjusted_construction)],
            ["Cost Uplift Commentary", uplift_note],
        ],
        colWidths=[70 * mm, 110 * mm],
    )
    topo_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ECFDF5")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(topo_tbl)
    story.append(Spacer(1, 8))

    story.append(Paragraph("5. Recommended Additional Checks (Before Unconditional Contract)", styles["H2"]))
    for bullet in [
        "- Full title/restrictions/easements legal review and covenant test.",
        "- Detailed civil design check for stormwater outfall and authority contributions.",
        "- Feature and level survey to validate slope/retaining assumptions.",
        "- Arborist and environmental screening for permit-risk vegetation.",
        "- Geotechnical investigation for excavation, slab, and retaining strategy.",
    ]:
        story.append(Paragraph(bullet, styles["BodyTight"]))
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "Disclaimer: This report is a screening-grade due diligence output using public GIS APIs and heuristic cost assumptions. "
        "It is not a substitute for formal planning, engineering, valuation, or legal advice.",
        styles["BodyTight"],
    ))

    doc.build(story)
    return pdf_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate comprehensive GIS due diligence PDF for a site.")
    parser.add_argument("--address", required=True, help="Site address label for report header.")
    parser.add_argument("--lat", type=float, required=True, help="Latitude in WGS84.")
    parser.add_argument("--lon", type=float, required=True, help="Longitude in WGS84.")
    parser.add_argument("--base-build-rate", type=float, default=2600.0, help="Baseline construction rate $/m².")
    args = parser.parse_args()

    pdf = build_report(args)
    print(pdf)


if __name__ == "__main__":
    main()
