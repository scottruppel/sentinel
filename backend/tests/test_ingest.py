"""Tests for BOM ingestion: parser, normalizer, and column detection."""
import pytest

from sentinel.ingest.normalizer import normalize_mpn
from sentinel.ingest.parser import parse_csv, parse_excel, _detect_columns


class TestNormalizeMPN:
    def test_basic_uppercase(self):
        assert normalize_mpn("adar1000bcpz") == "ADAR1000BCPZ"

    def test_strip_whitespace(self):
        assert normalize_mpn("  AD9363BBCZ  ") == "AD9363BBCZ"

    def test_remove_digikey_suffix(self):
        assert normalize_mpn("ADAR1000BCPZ-ND") == "ADAR1000BCPZ"
        assert normalize_mpn("ADP7118ACPZN-3.3-R7-1-ND") == "ADP7118ACPZN-3.3-R7"

    def test_remove_pbf_suffix(self):
        assert normalize_mpn("LTC6655BHMS8-3.3#PBF") == "LTC6655BHMS8-3.3"

    def test_remove_packaging_suffix(self):
        assert normalize_mpn("RC0402FR-0710KL-REEL") == "RC0402FR-0710KL"
        assert normalize_mpn("GRM155R71C104KA88D/TAPE") == "GRM155R71C104KA88D"

    def test_collapse_internal_spaces(self):
        assert normalize_mpn("XC7Z010 1CLG225C") == "XC7Z0101CLG225C"

    def test_empty_string(self):
        assert normalize_mpn("") == ""


class TestColumnDetection:
    def test_standard_headers(self):
        headers = ["Reference", "Manufacturer Part Number", "Manufacturer", "Description", "Qty"]
        mapping, warnings = _detect_columns(headers)
        assert "mpn" in mapping
        assert "manufacturer" in mapping
        assert "quantity" in mapping
        assert len(warnings) == 0

    def test_alternate_headers(self):
        headers = ["Ref Des", "MFR PN", "MFG", "Desc", "Count", "Value"]
        mapping, warnings = _detect_columns(headers)
        assert "mpn" in mapping
        assert "manufacturer" in mapping
        assert "reference_designator" in mapping

    def test_fallback_part_number(self):
        headers = ["Ref", "Component Part Number", "Vendor", "Amount"]
        mapping, warnings = _detect_columns(headers)
        assert "mpn" in mapping

    def test_no_mpn_raises(self):
        headers = ["Color", "Size", "Weight"]
        with pytest.raises(ValueError, match="Cannot identify"):
            _detect_columns(headers)


class TestCSVParser:
    def test_parse_basic_csv(self):
        csv_content = b"Reference,Manufacturer Part Number,Manufacturer,Description,Qty,Value,Package,Category\n"
        csv_content += b"U1,ADAR1000BCPZ,Analog Devices,Beamformer,1,,LFCSP-52,IC\n"
        csv_content += b"R1,RC0402FR-0710KL,Yageo,10k Resistor,10,10k,0402,Resistor\n"

        result = parse_csv(csv_content)
        assert len(result.components) == 2
        assert result.components[0].mpn == "ADAR1000BCPZ"
        assert result.components[0].mpn_normalized == "ADAR1000BCPZ"
        assert result.components[1].quantity == 10

    def test_duplicate_mpn_merges(self):
        csv_content = b"Ref Des,MPN,Manufacturer,Qty\n"
        csv_content += b"U1,ADAR1000BCPZ,ADI,2\n"
        csv_content += b"U1,ADAR1000BCPZ,ADI,3\n"

        result = parse_csv(csv_content)
        assert len(result.components) == 1
        assert result.components[0].quantity == 5
        assert any("Duplicate" in w.warning for w in result.warnings)

    def test_empty_rows_skipped(self):
        csv_content = b"Ref,Part Number,Manufacturer,Qty\n"
        csv_content += b"U1,AD9363BBCZ,ADI,1\n"
        csv_content += b",,,\n"
        csv_content += b"U2,ADF4159CCPZ,ADI,1\n"

        result = parse_csv(csv_content)
        assert len(result.components) == 2

    def test_too_short_csv_raises(self):
        with pytest.raises(ValueError, match="at least"):
            parse_csv(b"Header1,Header2\n")

    def test_bom_encoding(self):
        csv_content = "\ufeffReference,Manufacturer Part Number,Qty\nU1,AD9363BBCZ,1\n".encode("utf-8-sig")
        result = parse_csv(csv_content)
        assert len(result.components) == 1


class TestSeedBOM:
    def test_parse_cn0566_seed(self):
        from pathlib import Path
        csv_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "data" / "cn0566_bom.csv"
        if not csv_path.exists():
            pytest.skip("Seed BOM CSV not found")

        result = parse_csv(csv_path.read_bytes())
        assert len(result.components) >= 50
        mpns = [c.mpn_normalized for c in result.components]
        assert "ADAR1000BCPZ" in mpns
        assert "AD9363BBCZ" in mpns
        assert "XC7Z010-1CLG225C" in mpns
