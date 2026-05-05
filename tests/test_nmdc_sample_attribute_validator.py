"""Tests for NMDC sample attribute validation."""

from nmdc_sfas_brcs.validators.nmdc_sample_attribute_validator import (
    SampleAttributeSet,
    StudyContext,
    fetch_nmdc_biosample_attributes,
    normalize_field_name,
    validate_study_sample_attributes,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(self.pages.pop(0))


def test_normalize_field_name_matches_simple_variants():
    assert normalize_field_name("Collection Date") == "collection_date"
    assert normalize_field_name("soil-pH") == "soil_ph"


def test_fetch_nmdc_biosample_attributes_unions_keys_across_pages():
    session = FakeSession(
        [
            {
                "resources": [
                    {"id": "nmdc:bsm-1", "ph": 6.4},
                    {"id": "nmdc:bsm-2", "depth": {"has_numeric_value": 10}},
                ],
                "next_page_token": "token-2",
            },
            {"resources": [{"id": "nmdc:bsm-3", "water_content": 0.2}]},
        ]
    )

    result = fetch_nmdc_biosample_attributes(
        "nmdc:sty-11-test",
        session=session,
        api_base="https://example.org/nmdcschema",
        page_size=2,
    )

    assert result.sample_count == 3
    assert result.attributes == frozenset({"id", "ph", "depth", "water_content"})
    assert session.calls[1]["params"]["page_token"] == "token-2"


def test_validate_study_sample_attributes_reports_coverage_and_gaps():
    study = {
        "variables": [
            {
                "name": "air temperature",
                "roles": ["COVARIATE", "MEASURED_VARIABLE"],
                "value_type": "NUMERIC",
                "source_field_names": ["avg_temp"],
            },
            {
                "name": "host crop",
                "roles": ["GROUPING"],
                "value_type": "CATEGORICAL",
                "source_field_names": ["crop"],
                "mixs_terms": [{"id": "MIXS:0000248", "label": "host common name"}],
            },
            {
                "name": "transcript activity",
                "roles": ["MEASURED_VARIABLE"],
                "value_type": "ARRAY",
                "source_field_names": ["transcript_abundance"],
            },
            {
                "name": "sampling season",
                "roles": ["DATE_TIME_VARIABLE"],
                "value_type": "CATEGORICAL",
                "source_field_names": ["season"],
                "mixs_terms": [{"id": "MIXS:0000829", "label": "season"}],
            },
        ]
    }
    context = StudyContext(
        nmdc_study_id="nmdc:sty-11-test",
        study_name="Example study",
        program_id="nmdc_sfas_brcs:test",
        program_name="Test Program",
        study=study,
    )
    sample_attributes = SampleAttributeSet(
        nmdc_study_id="nmdc:sty-11-test",
        sample_count=2,
        attributes=frozenset({"id", "avg_temp", "host_common_name", "collection_date"}),
    )

    result = validate_study_sample_attributes(context, sample_attributes)

    assert result.matched_sample_attributes == frozenset({"avg_temp", "host_common_name"})
    assert result.matched_source_fields == frozenset({"avg_temp"})
    assert result.matched_by_mixs == frozenset({"host_common_name"})
    assert result.uncovered_sample_attributes == frozenset({"collection_date"})
    assert [v.variable_name for v in result.variables_without_sample_attribute] == [
        "sampling season"
    ]
