"""Тесты расчётных функций. Запуск: pytest (из корня репозитория)."""
import geopandas as gpd
import pytest
from shapely.geometry import Point

from geo_utils import nearest_distance, share_within, to_metric

UTM_EKB = "EPSG:32641"  # зона UTM 41N, Екатеринбург


def layer(coords, crs=UTM_EKB):
    return gpd.GeoDataFrame(geometry=[Point(x, y) for x, y in coords], crs=crs)


def test_to_metric_converts_degrees_to_utm():
    ekb = layer([(60.6, 56.84)], crs="EPSG:4326")
    assert to_metric(ekb).crs.to_epsg() == 32641


def test_to_metric_requires_crs():
    with pytest.raises(ValueError):
        to_metric(gpd.GeoDataFrame(geometry=[Point(0, 0)]))


def test_nearest_distance_in_meters():
    sources = layer([(0, 0)])
    targets = layer([(300, 400)])  # 3-4-5: ровно 500 м
    assert nearest_distance(targets, sources).iloc[0] == pytest.approx(500)


def test_share_within_counts_border_as_inside():
    sources = layer([(0, 0)])
    targets = layer([(100, 0), (500, 0), (600, 0)])
    assert share_within(targets, sources, 500) == pytest.approx(2 / 3)


def test_share_within_rejects_degrees():
    sources = layer([(60.6, 56.84)], crs="EPSG:4326")
    targets = layer([(60.61, 56.84)], crs="EPSG:4326")
    with pytest.raises(ValueError, match="метрической"):
        share_within(targets, sources, 500)


def test_share_within_empty_targets():
    assert share_within(layer([]), layer([(0, 0)]), 500) == 0.0
