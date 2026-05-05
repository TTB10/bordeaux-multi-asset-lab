"""Unit tests for UniverseLoader."""

from __future__ import annotations

from pathlib import Path

import pytest

from bml.universe import (
    AssetClass,
    Region,
    Universe,
    UniverseLoader,
    UniverseLoaderError,
)


class TestUniverseLoaderShipped:
    """Tests against the real shipped universe.yaml."""

    def test_loads_successfully(self) -> None:
        u = UniverseLoader.load()
        assert isinstance(u, Universe)
        assert len(u) >= 30, f"Expected at least 30 assets, got {len(u)}"

    def test_covers_main_asset_classes(self) -> None:
        u = UniverseLoader.load()
        classes = {a.asset_class for a in u}
        for required in (
            AssetClass.EQUITY_DM,
            AssetClass.EQUITY_EM,
            AssetClass.GOVERNMENT_BOND,
            AssetClass.CREDIT_IG,
            AssetClass.CREDIT_HY,
            AssetClass.GOLD,
            AssetClass.CASH,
        ):
            assert required in classes, f"Missing asset class: {required}"

    def test_covers_main_regions(self) -> None:
        u = UniverseLoader.load()
        regions = {a.region for a in u}
        for required in (Region.USA, Region.EUROZONE, Region.GLOBAL, Region.EMERGING):
            assert required in regions, f"Missing region: {required}"

    def test_all_isins_are_unique(self) -> None:
        u = UniverseLoader.load()
        isins = [a.isin for a in u]
        assert len(isins) == len(set(isins))

    def test_all_ter_below_one_percent(self) -> None:
        """No fund should have TER above 1% in this universe."""
        u = UniverseLoader.load()
        expensive = [a for a in u if a.ter > 0.01]
        assert not expensive, f"Funds with TER > 1%: {[a.ticker for a in expensive]}"


class TestUniverseLoaderErrors:
    """Tests for error paths using synthetic YAML files."""

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            UniverseLoader.load(tmp_path / "does_not_exist.yaml")

    def test_invalid_yaml_syntax_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.yaml"
        f.write_text("[unclosed list\n", encoding="utf-8")
        with pytest.raises(UniverseLoaderError, match="Invalid YAML"):
            UniverseLoader.load(f)

    def test_wrong_root_type_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "list_root.yaml"
        f.write_text("- a\n- b\n", encoding="utf-8")
        with pytest.raises(UniverseLoaderError, match="must be a mapping"):
            UniverseLoader.load(f)

    def test_invalid_isin_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "bad_isin.yaml"
        f.write_text(
            "assets:\n"
            "  - {ticker: TEST, isin: TOOSHORT, name: Test, "
            "asset_class: gold, region: global, currency: USD, ter: 0.001}\n",
            encoding="utf-8",
        )
        with pytest.raises(UniverseLoaderError, match="validation failed"):
            UniverseLoader.load(f)

    def test_unknown_asset_class_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "bad_class.yaml"
        f.write_text(
            "assets:\n"
            "  - {ticker: TEST, isin: IE00B5BMR087, name: Test, "
            "asset_class: crypto_bag, region: global, currency: USD, ter: 0.001}\n",
            encoding="utf-8",
        )
        with pytest.raises(UniverseLoaderError, match="validation failed"):
            UniverseLoader.load(f)

    def test_duplicate_isin_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "dup.yaml"
        f.write_text(
            "assets:\n"
            "  - {ticker: A, isin: IE00B5BMR087, name: A, asset_class: gold, "
            "region: global, currency: USD, ter: 0.001}\n"
            "  - {ticker: B, isin: IE00B5BMR087, name: B, asset_class: gold, "
            "region: global, currency: USD, ter: 0.001}\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="Duplicate ISIN"):
            UniverseLoader.load(f)
