"""Общие функции пространственных расчётов проекта.

Функции вынесены из ноутбуков, чтобы их можно было проверять автоматическими тестами
(tests/test_geo_utils.py) и использовать в нескольких ноутбуках одинаково.
В ноутбуке подключайте так:

    import sys; sys.path.append(str(BASE / "src"))   # в Colab BASE — папка на Диске с копией src/
    from geo_utils import to_metric, share_within
"""
from __future__ import annotations

import geopandas as gpd


def to_metric(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Возвращает слой в метрической проекции (зона UTM по центру слоя).

    Если слой уже в метрах, возвращает его без изменений.
    Если система координат не задана, выдаёт ошибку: угадывать её нельзя.
    """
    if gdf.crs is None:
        raise ValueError("У слоя не задана система координат (CRS)")
    if gdf.crs.is_projected:
        return gdf
    return gdf.to_crs(gdf.estimate_utm_crs())


def _require_metric(*layers: gpd.GeoDataFrame) -> None:
    for layer in layers:
        if layer.crs is None or not layer.crs.is_projected:
            raise ValueError("Расстояния считаются только в метрической проекции. Вызовите to_metric()")
    if len({layer.crs for layer in layers}) > 1:
        raise ValueError("Слои в разных системах координат. Приведите их к одной")


def nearest_distance(targets: gpd.GeoDataFrame, sources: gpd.GeoDataFrame) -> gpd.GeoSeries:
    """Расстояние в метрах от каждого объекта targets до ближайшего объекта sources."""
    _require_metric(targets, sources)
    if sources.empty:
        raise ValueError("Слой sources пуст: расстояние до ближайшего объекта не определено")
    joined = gpd.sjoin_nearest(targets[["geometry"]], sources[["geometry"]], how="left", distance_col="dist")
    return joined.groupby(level=0)["dist"].min().reindex(targets.index)


def share_within(targets: gpd.GeoDataFrame, sources: gpd.GeoDataFrame, distance_m: float) -> float:
    """Доля объектов targets, у которых ближайший объект sources не дальше distance_m метров."""
    if distance_m <= 0:
        raise ValueError("Расстояние должно быть положительным")
    if targets.empty:
        return 0.0
    dist = nearest_distance(targets, sources)
    return float((dist <= distance_m).mean())
