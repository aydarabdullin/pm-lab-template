"""Проверка качества слоёв в data/processed по правилам из data/validation.json.

Запуск из корня репозитория:  python scripts/validate_data.py
Код выхода 1, если найдена хотя бы одна ошибка: так проверка останавливает Pull Request в CI.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
RULES = json.loads((ROOT / "data" / "validation.json").read_text(encoding="utf-8"))


def check_layer(name: str, rule: dict) -> list[str]:
    path = PROCESSED / f"{name}.gpkg"
    if not path.exists():
        return [f"нет файла {path.relative_to(ROOT)}"]
    errors = []
    size_mb = path.stat().st_size / 1024 / 1024
    if size_mb > RULES.get("max_file_mb", 10):
        errors.append(f"файл {size_mb:.1f} МБ больше {RULES['max_file_mb']} МБ")
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        errors.append("не задана система координат")
    elif RULES.get("crs") and gdf.crs != RULES["crs"]:
        errors.append(f"система координат {gdf.crs.to_string()}, ожидается {RULES['crs']}")
    if len(gdf) < rule.get("min_count", 1):
        errors.append(f"объектов {len(gdf)}, ожидается не меньше {rule['min_count']}")
    if gdf.geometry.isna().any() or gdf.is_empty.any():
        errors.append(f"пустых геометрий: {int(gdf.geometry.isna().sum() + gdf.is_empty.sum())}")
    invalid = int((~gdf.is_valid).sum())
    if invalid:
        errors.append(f"некорректных геометрий: {invalid} (исправьте через make_valid)")
    allowed = set(rule.get("geometry", []))
    wrong = sorted(set(gdf.geom_type.dropna()) - allowed) if allowed else []
    if wrong:
        errors.append(f"лишние типы геометрии: {', '.join(wrong)}")
    for col in rule.get("required", []):
        if col not in gdf.columns:
            errors.append(f"нет обязательного поля {col}")
    id_cols = rule.get("id")
    if id_cols and all(c in gdf.columns for c in id_cols):
        dups = int(gdf.duplicated(id_cols).sum())
        if dups:
            errors.append(f"дубликатов по {'+'.join(id_cols)}: {dups}")
    if "bbox" in RULES and gdf.crs is not None and not gdf.empty:
        minx, miny, maxx, maxy = gdf.to_crs(4326).total_bounds
        bx0, by0, bx1, by1 = RULES["bbox"]
        if minx < bx0 or miny < by0 or maxx > bx1 or maxy > by1:
            errors.append("объекты выходят за границы территории проекта (bbox)")
    return errors


def main() -> int:
    if not any(PROCESSED.glob("*.gpkg")):
        print("В data/processed пока нет слоёв, проверка пропущена")
        return 0
    failed = 0
    for name, rule in RULES["layers"].items():
        errors = check_layer(name, rule)
        if errors:
            failed += 1
            print(f"ОШИБКА  {name}: " + "; ".join(errors))
        else:
            print(f"OK      {name}")
    print(f"\nСлоёв с ошибками: {failed} из {len(RULES['layers'])}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
