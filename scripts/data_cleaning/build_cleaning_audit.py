#!/usr/bin/env python3
"""Build an auditable, loss-preserving cleaned job dataset from available raw exports.

This deliberately does not infer exchange rates, annualize non-yearly salaries, fill
missing salaries, fuzzy-match job titles, or delete duplicates/outliers. All raw source
columns are retained in ``source_row_json`` and the original source files are read-only.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import email.utils
import gzip
import hashlib
import json
import math
import re
import sqlite3
import statistics
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIRECTORY = PROJECT_ROOT / "scripts" / "data_cleaning"
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

import build_site_data as source_reader  # noqa: E402

DEFAULT_RAW_DIRECTORY = PROJECT_ROOT / "data" / "raw"
DEFAULT_DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "jobs_cleaned_audited.csv.gz"
DEFAULT_REPORT_DIRECTORY = PROJECT_ROOT / "analysis" / "reports" / "data_cleaning"
DEFAULT_NOTEBOOK_PATH = PROJECT_ROOT / "analysis" / "notebooks" / "cleaning_data_audit.ipynb"

INTERNATIONAL_SOURCE = source_reader.INTERNATIONAL_JOB_SOURCE_FILE
MERGED_SOURCE = source_reader.MERGED_EXCEL_WORKBOOK_SOURCE_FILE
ARAB_SOURCE = source_reader.ARAB_TECH_SOURCE_FILE
CYBER_SOURCE = source_reader.CYBERSECURITY_JOB_SOURCE_FILE
REMOTE_ENRICHED = "remote_tech_jobs_foreign_after_adding_skills.csv"
STARTUP_ENRICHED = "startup_jobs_foreign_after_adding_skills.csv"
JOOBLE_ENRICHED = "tech_jobs_jooble_careerjet_AGNABY_after_adding_skills.csv"

# Only the enriched copy is emitted as a job record. Its base copy is read separately
# to audit row IDs and skill changes, never concatenated as another set of jobs.
JOB_SOURCE_SPECS: list[dict[str, Any]] = [
    {"file": INTERNATIONAL_SOURCE, "dataset": "international_jobs", "bucket": "historical_2023_sample", "kind": "csv", "required": True},
    {"file": MERGED_SOURCE, "dataset": "merged_tech_jobs", "bucket": "other_snapshot", "kind": "xlsx", "required": True},
    {"file": ARAB_SOURCE, "dataset": "arab_tech_jobs", "bucket": "other_snapshot", "kind": "csv", "required": True},
    {"file": CYBER_SOURCE, "dataset": "cybersecurity_jobs", "bucket": "other_snapshot", "kind": "csv", "required": True},
    {"file": REMOTE_ENRICHED, "dataset": "remote_tech_jobs", "bucket": "latest_export_unverified", "kind": "csv", "required": True},
    {"file": STARTUP_ENRICHED, "dataset": "startup_jobs", "bucket": "latest_export_unverified", "kind": "csv", "required": True},
    {"file": JOOBLE_ENRICHED, "dataset": "jooble_careerjet_jobs", "bucket": "latest_export_unverified", "kind": "csv", "required": True},
]

BASE_EXPORTS: dict[str, str] = {
    REMOTE_ENRICHED: "remote_tech_jobs_foreign.csv",
    STARTUP_ENRICHED: "startup_jobs_foreign.csv",
    JOOBLE_ENRICHED: "tech_jobs_jooble_careerjet_AGNABY.csv",
}

REFERENCE_ONLY_FILES = set(BASE_EXPORTS.values())
ALL_EXPECTED_FILES = [
    INTERNATIONAL_SOURCE,
    MERGED_SOURCE,
    ARAB_SOURCE,
    CYBER_SOURCE,
    REMOTE_ENRICHED,
    STARTUP_ENRICHED,
    JOOBLE_ENRICHED,
    *BASE_EXPORTS.values(),
]

EMPTY_TEXT = {"", "null", "none", "nan", "n/a", "na", "<na>"}

# These are explicit lexical aliases only. Unrecognized values are preserved after
# whitespace cleanup; no fuzzy country matching or location-to-country inference occurs.
COUNTRY_ALIASES = {
    "us": "United States",
    "u.s.": "United States",
    "u.s.a.": "United States",
    "usa": "United States",
    "united states of america": "United States",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "great britain": "United Kingdom",
    "britain": "United Kingdom",
    "uae": "United Arab Emirates",
    "u.a.e.": "United Arab Emirates",
    "ksa": "Saudi Arabia",
    "kingdom of saudi arabia": "Saudi Arabia",
    "remote anywhere": "Remote (Anywhere)",
    "anywhere": "Remote (Anywhere)",
    "world-wide": "Worldwide",
    "other": "Other/Unknown",
    "unknown": "Other/Unknown",
}

CURRENCY_CODES = {
    "USD", "EGP", "SAR", "AED", "QAR", "JOD", "KWD", "OMR", "BHD", "MAD",
    "INR", "CAD", "AUD", "EUR", "GBP", "CHF", "NZD", "SGD", "BRL", "MXN",
    "PLN", "SEK", "NOK", "DKK", "ZAR", "JPY", "CNY", "HKD", "TWD", "TRY",
    "PKR", "BDT", "IDR", "MYR", "THB", "PHP", "CZK", "HUF", "RON", "ILS",
}
CURRENCY_TEXT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("USD", re.compile(r"\bUSD\b|\bUS\s*\$|\bUS dollars?\b", re.I)),
    ("CAD", re.compile(r"\bCAD\b|\bCA\s*\$|\bC\s*\$", re.I)),
    ("AUD", re.compile(r"\bAUD\b|\bAU\s*\$|\bA\s*\$", re.I)),
    ("NZD", re.compile(r"\bNZD\b|\bNZ\s*\$", re.I)),
    ("SGD", re.compile(r"\bSGD\b", re.I)),
    ("EGP", re.compile(r"\bEGP\b|Egyptian pounds?|جنيه\s*مصري|جنيه\s*مصرى", re.I)),
    ("SAR", re.compile(r"\bSAR\b|Saudi riyals?|ريال\s*سعودي", re.I)),
    ("AED", re.compile(r"\bAED\b|UAE dirhams?|Emirati dirhams?|درهم\s*إماراتي|درهم\s*اماراتي", re.I)),
    ("QAR", re.compile(r"\bQAR\b|Qatari riyals?|ريال\s*قطري", re.I)),
    ("JOD", re.compile(r"\bJOD\b|Jordanian dinars?", re.I)),
    ("KWD", re.compile(r"\bKWD\b|Kuwaiti dinars?", re.I)),
    ("OMR", re.compile(r"\bOMR\b|Omani rials?", re.I)),
    ("BHD", re.compile(r"\bBHD\b|Bahraini dinars?", re.I)),
    ("MAD", re.compile(r"\bMAD\b|Moroccan dirhams?", re.I)),
    ("INR", re.compile(r"\bINR\b|Indian rupees?|₹", re.I)),
    ("EUR", re.compile(r"\bEUR\b|€|euros?", re.I)),
    ("GBP", re.compile(r"\bGBP\b|£|pounds? sterling", re.I)),
    ("CHF", re.compile(r"\bCHF\b|Swiss francs?", re.I)),
    ("BRL", re.compile(r"\bBRL\b|R\$", re.I)),
    ("MXN", re.compile(r"\bMXN\b|Mex\$", re.I)),
    ("PLN", re.compile(r"\bPLN\b|zł", re.I)),
    ("SEK", re.compile(r"\bSEK\b", re.I)),
    ("NOK", re.compile(r"\bNOK\b", re.I)),
    ("DKK", re.compile(r"\bDKK\b", re.I)),
    ("ZAR", re.compile(r"\bZAR\b", re.I)),
    ("JPY", re.compile(r"\bJPY\b|\bJapanese yen\b", re.I)),
    ("CNY", re.compile(r"\bCNY\b|\bRMB\b|\bChinese yuan\b", re.I)),
    ("HKD", re.compile(r"\bHKD\b", re.I)),
    ("TWD", re.compile(r"\bTWD\b", re.I)),
    ("TRY", re.compile(r"\bTRY\b|Turkish lira", re.I)),
    ("PKR", re.compile(r"\bPKR\b", re.I)),
    ("BDT", re.compile(r"\bBDT\b", re.I)),
    ("IDR", re.compile(r"\bIDR\b", re.I)),
    ("MYR", re.compile(r"\bMYR\b", re.I)),
    ("THB", re.compile(r"\bTHB\b", re.I)),
    ("PHP", re.compile(r"\bPHP\b", re.I)),
    ("CZK", re.compile(r"\bCZK\b", re.I)),
    ("HUF", re.compile(r"\bHUF\b", re.I)),
    ("RON", re.compile(r"\bRON\b", re.I)),
    ("ILS", re.compile(r"\bILS\b|Israeli new shekels?", re.I)),
]

NUMBER_TOKEN_PATTERN = re.compile(
    r"(?<![\w.])(?:\d{1,3}(?:\s+\d{3})+|\d[\d.,]*)(?:\s*[kKmMbB](?:n)?)?(?!\w)"
)
ARABIC_DIGIT_TRANSLATION = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
MOJIBAKE_PATTERN = re.compile(r"(?:\ufffd|Ã.|â(?:\x80|€|€™|€)|\x80\x94)")
NON_DISCLOSURE_TERMS = (
    "not disclosed", "not specified", "not provided", "not available", "not mentioned",
    "not listed", "undisclosed", "confidential", "amount not disclosed", "unspecified",
    "no data", "not found", "negotiable", "competitive", "competitive salary",
)
# Deliberately broad screening bounds only; they create a manual-review flag, never a
# correction or deletion. They are currency-unit agnostic, so users should review context.
ABSOLUTE_VALUE_REVIEW_BOUNDS = {
    "YEAR": (1_000.0, 1_000_000_000.0),
    "MONTH": (10.0, 100_000_000.0),
    "WEEK": (1.0, 100_000_000.0),
    "DAY": (0.1, 10_000_000.0),
    "HOUR": (0.1, 1_000_000.0),
}
ESTIMATE_EVIDENCE_TERMS = (
    "benchmark", "estimate", "estimated", "inference", "proxy", "paylab", "indeed",
    "bureau of labor statistics", "bls.gov", "market range", "salary guide", "salary guides",
    "interpolat", "sourced", "verified respondents", "respondents", "median annual wage",
)

PRE_QUALITY_FIELDS = (
    "title", "company", "country", "description", "source_url", "skills",
    "salary_raw_numeric", "salary_any_numeric_source", "explicit_posted_date", "source_updated_at", "source_collection_date",
)

OUTPUT_FIELDS = [
    "record_id",
    "source_dataset",
    "source_file",
    "source_row_number",
    "source_record_id",
    "source_record_id_duplicate_occurrence",
    "record_origin",
    "source_platform",
    "title_raw",
    "title_clean",
    "title_key",
    "company_raw",
    "company_clean",
    "country_raw",
    "country_standardized",
    "location_scope",
    "city_raw",
    "region_raw",
    "location_raw",
    "work_mode_raw",
    "remote_flag_raw",
    "employment_type_raw",
    "experience_raw",
    "experience_years_min",
    "experience_years_max",
    "experience_parse_status",
    "category_raw",
    "description_raw",
    "description_char_count",
    "posted_at_raw",
    "posted_at_iso",
    "source_updated_at_raw",
    "source_updated_at_iso",
    "source_collected_at_raw",
    "source_collected_at_iso",
    "collection_date_field",
    "source_date_field",
    "date_quality_flags",
    "salary_raw",
    "salary_candidate_raw",
    "salary_source_field_used",
    "salary_local_source_value",
    "salary_usd_source_value",
    "salary_range_est_source_value",
    "salary_currency_raw",
    "salary_basis_raw",
    "salary_rate_raw",
    "salary_source_raw",
    "salary_sources_raw",
    "salary_fill_source_raw",
    "salary_estimate_source_url",
    "salary_estimate_source_date",
    "salary_estimate_source_date_status",
    "salary_value_type",
    "salary_provenance_status",
    "salary_parse_status",
    "salary_amount_1_original_currency",
    "salary_amount_2_original_currency",
    "salary_min_original_currency",
    "salary_max_original_currency",
    "salary_midpoint_original_currency",
    "salary_range_kind",
    "salary_currency_code",
    "salary_currency_detection_status",
    "salary_period_code",
    "salary_period_detection_status",
    "salary_annualized_min_native",
    "salary_annualized_max_native",
    "salary_annualized_midpoint_native",
    "salary_reporting_currency",
    "salary_fx_rate_to_reporting_currency",
    "salary_fx_rate_source",
    "salary_fx_rate_date",
    "salary_annualized_min_reporting_currency",
    "salary_annualized_max_reporting_currency",
    "salary_comparability_status",
    "salary_statistics_eligible",
    "salary_integrity_flags",
    "salary_iqr_outlier_flag",
    "skills_raw",
    "skills_base_raw",
    "skills_tokens_json",
    "skill_ids_json",
    "skill_token_count_raw",
    "skill_token_count_unique",
    "skill_canonical_id_count",
    "skill_duplicate_token_count",
    "skills_source_raw",
    "skills_enrichment_status",
    "source_url_raw",
    "source_url_syntax_status",
    "listing_status",
    "snapshot_type",
    "exact_duplicate_within_source",
    "encoding_suspected_mojibake",
    "data_quality_flags",
    "source_row_json",
]

INTERMEDIATE_FIELDS = [field for field in OUTPUT_FIELDS if field != "salary_iqr_outlier_flag"]


def collapse_whitespace(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u00a0", " ").replace("\u2007", " ").replace("\u202f", " ")
    return re.sub(r"\s+", " ", text).strip()


def raw_field(row: Mapping[str, Any], *names: str) -> str:
    """Return the first physically nonblank source value without changing its text."""
    lowered = {str(key).strip().casefold(): value for key, value in row.items()}
    for name in names:
        value = lowered.get(name.casefold())
        if value is not None and str(value).strip():
            return str(value)
    return ""


def source_value(row: Mapping[str, Any], *names: str) -> str:
    return source_reader.first_available_source_value(dict(row), *names)


def country_standardized(value: str) -> str:
    cleaned = collapse_whitespace(value)
    if not cleaned or not source_reader.contains_source_value(cleaned):
        return ""
    key = cleaned.casefold().replace("’", "'")
    return COUNTRY_ALIASES.get(key, cleaned)


def first_valid_raw_field(row: Mapping[str, Any], *names: str) -> str:
    """Prefer the first non-placeholder value while preserving its exact source text."""
    for name in names:
        value = raw_field(row, name)
        if source_reader.contains_source_value(value):
            return value
    return raw_field(row, *names)


def country_location_scope(value: str) -> str:
    folded = collapse_whitespace(value).casefold()
    if not folded:
        return "unknown_or_missing"
    if folded in {"remote (anywhere)", "worldwide", "global", "remote"}:
        return "geographic_scope_not_country"
    if folded in {"other/unknown", "unknown", "other"}:
        return "unknown_or_missing"
    return "country_label_unverified"


def parse_experience_years(value: str) -> tuple[str, str, str]:
    text = collapse_whitespace(value).casefold()
    if not text or text in EMPTY_TEXT or "null yrs" in text:
        return "", "", "missing_or_unavailable"
    match = re.search(r"(?<!\d)(\d{1,2})\s*[-–—]\s*(\d{1,2})(?!\d)", text)
    if match:
        low, high = int(match.group(1)), int(match.group(2))
        if low <= high:
            return str(low), str(high), "explicit_range"
        return str(low), str(high), "reversed_range_review"
    match = re.search(r"(?<!\d)(\d{1,2})\s*\+", text)
    if match:
        return match.group(1), "", "explicit_lower_bound_only"
    match = re.search(r"(?<!\d)(\d{1,2})\s*(?:years?|yrs?)\b", text)
    if match:
        return match.group(1), match.group(1), "explicit_single_value"
    return "", "", "not_parseable_as_years"


def parse_number_token(token: str) -> float | None:
    normalized = collapse_whitespace(token).casefold().replace("−", "-")
    # Spaces between groups of three digits are thousands separators in some exports.
    normalized = re.sub(r"(?<=\d)\s+(?=\d{3}(?:\D|$))", "", normalized)
    suffix_match = re.search(r"\s*([kmb])(?:n)?$", normalized)
    multiplier = 1.0
    if suffix_match:
        multiplier = {"k": 1_000.0, "m": 1_000_000.0, "b": 1_000_000_000.0}[suffix_match.group(1)]
        normalized = normalized[: suffix_match.start()].strip()

    if not normalized or not re.fullmatch(r"\d[\d.,]*", normalized):
        return None

    if "," in normalized and "." in normalized:
        if normalized.rfind(",") > normalized.rfind("."):
            normalized = normalized.replace(".", "").replace(",", ".")
        else:
            normalized = normalized.replace(",", "")
    elif "," in normalized or "." in normalized:
        separator = "," if "," in normalized else "."
        pieces = normalized.split(separator)
        if len(pieces) > 1 and all(len(piece) == 3 for piece in pieces[1:]):
            normalized = "".join(pieces)
        elif len(pieces) == 2:
            normalized = pieces[0] + "." + pieces[1]
        else:
            normalized = "".join(pieces[:-1]) + "." + pieces[-1]

    try:
        number = float(normalized) * multiplier
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def parse_salary_text(text: str) -> dict[str, Any]:
    """Parse one or two amount tokens without assigning a currency or pay period."""
    normalized = collapse_whitespace(text).translate(ARABIC_DIGIT_TRANSLATION)
    normalized = normalized.replace("٬", ",").replace("٫", ".")
    matches = list(NUMBER_TOKEN_PATTERN.finditer(normalized))
    if not matches:
        return {"status": "no_numeric_amount", "amounts": [], "range_kind": ""}

    tokens = [match.group(0) for match in matches]
    values = [parse_number_token(token) for token in tokens]
    if any(value is None for value in values):
        return {"status": "unparseable_numeric_token", "amounts": [], "range_kind": ""}
    numeric_values = [float(value) for value in values if value is not None]

    # In compact ranges such as 90-130k, the suffix applies to both endpoints.
    if len(tokens) == 2:
        first_suffix = re.search(r"([kmb])(?:n)?$", tokens[0].strip(), re.I)
        second_suffix = re.search(r"([kmb])(?:n)?$", tokens[1].strip(), re.I)
        if not first_suffix and second_suffix and abs(numeric_values[0]) < 1_000:
            factor = {"k": 1_000.0, "m": 1_000_000.0, "b": 1_000_000_000.0}[second_suffix.group(1).casefold()]
            numeric_values[0] *= factor

    if len(numeric_values) > 2:
        return {"status": "multiple_numeric_tokens_review", "amounts": [], "range_kind": ""}
    if normalized.lstrip().startswith("-"):
        numeric_values[0] *= -1
    if len(numeric_values) == 1:
        return {"status": "parsed_single_amount", "amounts": numeric_values, "range_kind": "point"}
    status = "parsed_range" if numeric_values[0] <= numeric_values[1] else "range_order_reversed"
    return {"status": status, "amounts": numeric_values, "range_kind": "range"}


def _currency_from_text(text: str) -> tuple[str, str]:
    folded = collapse_whitespace(text)
    found = {code for code, pattern in CURRENCY_TEXT_PATTERNS if pattern.search(folded)}
    if len(found) == 1:
        return next(iter(found)), "explicit_text"
    if len(found) > 1:
        return "", "conflicting_currency_codes_in_text"
    if "$" in folded or "¥" in folded:
        return "", "ambiguous_currency_symbol"
    return "", "not_stated"


def _currency_from_column(value: str) -> tuple[str, str]:
    text = collapse_whitespace(value).upper()
    if not text:
        return "", "not_stated"
    # Some inherited values append a non-currency note (e.g. "MAD (proxy)").
    match = re.search(r"(?<![A-Z])([A-Z]{3})(?![A-Z])", text)
    if match and match.group(1) in CURRENCY_CODES:
        return match.group(1), "explicit_source_column"
    if text in {"$", "US$", "CA$", "AU$", "£", "€", "¥"}:
        return "", "ambiguous_currency_symbol"
    return "", "unrecognized_source_currency_value"


def detect_currency(raw_column: str, salary_text: str) -> tuple[str, str]:
    column_code, column_status = _currency_from_column(raw_column)
    text_code, text_status = _currency_from_text(salary_text)
    if column_code and text_code and column_code != text_code:
        return "", "conflict_between_source_column_and_salary_text"
    if column_code and text_code:
        return column_code, "explicit_source_column_and_text"
    if column_code:
        return column_code, column_status
    if text_code:
        return text_code, text_status
    if column_status == "unrecognized_source_currency_value":
        return "", column_status
    if text_status in {"ambiguous_currency_symbol", "conflicting_currency_codes_in_text"}:
        return "", text_status
    if column_status == "ambiguous_currency_symbol":
        return "", column_status
    return "", "not_stated"


def detect_period(text: str, period_fields: Iterable[str], source_field_used: str) -> tuple[str, str]:
    folded = collapse_whitespace(text).casefold()
    indicators: set[str] = set()
    patterns = {
        "YEAR": r"\b(?:annual|annually|yearly|per year|a year|/year|year|yr|pa)\b",
        "MONTH": r"\b(?:monthly|per month|a month|/month|month|monthly)\b|شهري",
        "WEEK": r"\b(?:weekly|per week|a week|/week|week)\b",
        "DAY": r"\b(?:daily|per day|a day|/day|day)\b",
        "HOUR": r"\b(?:hourly|per hour|an hour|/hour|hour)\b",
    }
    for period, pattern in patterns.items():
        if re.search(pattern, folded, re.I):
            indicators.add(period)
    if len(indicators) > 1:
        return "UNKNOWN", "conflicting_period_indicators_in_text"
    text_period = next(iter(indicators), "")

    field_periods: set[str] = set()
    for raw in period_fields:
        value = collapse_whitespace(raw).casefold()
        if not value:
            continue
        # Ignore generic provenance labels such as "posted", "sourced", or "proxy".
        field_indicator = set()
        for period, pattern in patterns.items():
            if re.search(pattern, value, re.I):
                field_indicator.add(period)
        if len(field_indicator) == 1:
            field_periods.update(field_indicator)
        elif len(field_indicator) > 1:
            return "UNKNOWN", "conflicting_period_indicators_in_source_fields"
    if source_field_used == "salary_year_avg":
        field_periods.add("YEAR")
    elif source_field_used == "salary_hour_avg":
        field_periods.add("HOUR")
    if len(field_periods) > 1:
        return "UNKNOWN", "conflicting_period_indicators_in_source_fields"
    field_period = next(iter(field_periods), "")
    if text_period and field_period and text_period != field_period:
        return "UNKNOWN", "conflict_between_salary_text_and_source_period"
    if text_period:
        return text_period, "explicit_in_salary_text"
    if field_period:
        return field_period, "explicit_in_source_period_field"
    return "UNKNOWN", "period_not_stated"


def _disclosure_only(text: str) -> bool:
    folded = collapse_whitespace(text).casefold()
    return bool(folded) and any(term in folded for term in NON_DISCLOSURE_TERMS)


def _estimate_evidence(*values: str) -> bool:
    joined = " ".join(collapse_whitespace(value).casefold() for value in values if value)
    return any(term in joined for term in ESTIMATE_EVIDENCE_TERMS)


def _extract_first_url(*values: str) -> str:
    for value in values:
        match = re.search(r"https?://[^\s;,)]+", value or "", re.I)
        if match:
            return match.group(0).rstrip(".,;:)]}")
    return ""


def _salary_candidate(row: Mapping[str, Any]) -> tuple[str, str, dict[str, Any]]:
    raw_salary = raw_field(row, "salary", "salary_raw")
    primary_parsed = parse_salary_text(raw_salary)
    if primary_parsed["amounts"] or _disclosure_only(raw_salary):
        return raw_salary, ("salary" if raw_field(row, "salary") else "salary_raw"), primary_parsed

    # Existing researched ranges and source-native aggregates are retained and labeled;
    # they are never treated as employer-posted salary unless explicitly supported.
    for field_name in ("salary_range_est", "salary_year_avg", "salary_hour_avg", "salary_local"):
        candidate = raw_field(row, field_name)
        if not candidate:
            continue
        parsed = parse_salary_text(candidate)
        if parsed["amounts"]:
            return candidate, field_name, parsed
    if raw_salary:
        return raw_salary, ("salary" if raw_field(row, "salary") else "salary_raw"), primary_parsed
    return "", "", {"status": "no_salary_value", "amounts": [], "range_kind": ""}


def _salary_value_class(
    source_dataset: str,
    candidate_field: str,
    candidate_text: str,
    raw_salary: str,
    basis: str,
    source_text: str,
    sources_text: str,
    fill_source: str,
    amounts: list[float],
) -> tuple[str, str]:
    if not amounts:
        if _disclosure_only(raw_salary or candidate_text):
            return "not_disclosed", "source contains non-disclosure or negotiable wording"
        if not source_reader.contains_source_value(raw_salary or candidate_text):
            return "missing", "no salary value supplied"
        return "unparseable_or_no_numeric_amount", "no reliable numeric amount could be extracted"

    if _estimate_evidence(basis, source_text, sources_text, fill_source):
        return "estimated_legacy_unverified", "pre-existing research/proxy/benchmark value; not revalidated for role, country, level, or source date"

    original_posting = "original (posting / source data)" in fill_source.casefold()
    explicitly_posted = "posted" in collapse_whitespace(basis).casefold()
    if source_dataset in {"remote_tech_jobs", "startup_jobs", "jooble_careerjet_jobs", "cybersecurity_jobs"} and candidate_field in {"salary", "salary_raw"}:
        return "actual_reported", "numeric salary text is present in the selected job-export/source row; not independently rechecked against a live listing"
    if source_dataset == "arab_tech_jobs" and (original_posting or explicitly_posted) and candidate_field in {"salary", "salary_raw"}:
        return "actual_reported", "source labels this numeric raw salary as posted/original; source listing was not independently rechecked"
    if source_dataset == "merged_tech_jobs" and candidate_field in {"salary", "salary_raw"}:
        if source_text and source_text.casefold().startswith("original (from source data"):
            return "source_reported_unverified", "source-origin value; posting status and currency/period provenance are not fully verified"
        return "source_reported_unverified", "merged snapshot does not establish whether this value is an employer-posted salary"
    if source_dataset == "arab_tech_jobs" and candidate_field == "salary_local" and (original_posting or explicitly_posted):
        return "source_reported_unverified", "numeric source-local value has no preserved original salary text for verification"
    if candidate_field in {"salary_range_est", "salary_local", "salary_year_avg", "salary_hour_avg"}:
        return "source_reported_unverified", "numeric source-derived field lacks sufficient evidence for an actual-posted label"
    return "source_reported_unverified", "numeric value is present but posting/estimate provenance is not established"


def format_number(value: float | int | None) -> str:
    if value is None:
        return ""
    number = float(value)
    if not math.isfinite(number):
        return ""
    if abs(number - round(number)) < 1e-9:
        return str(int(round(number)))
    return f"{number:.8f}".rstrip("0").rstrip(".")


def _source_row_digest(row: Mapping[str, Any]) -> str:
    material = json.dumps(
        {str(key): "" if value is None else str(value) for key, value in row.items()},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.blake2b(material.encode("utf-8"), digest_size=16).hexdigest()


def _date_field(row: Mapping[str, Any], *names: str) -> tuple[str, str]:
    value = first_valid_raw_field(row, *names)
    if not value or not source_reader.contains_source_value(value):
        return "", ""
    lowered = {str(key).strip().casefold(): key for key in row}
    for name in names:
        original_key = lowered.get(name.casefold())
        if original_key is not None and str(row.get(original_key, "")).strip():
            return value, str(original_key)
    return value, ""


def parse_source_datetime(value: str) -> dt.datetime | None:
    text = collapse_whitespace(value)
    if not text:
        return None

    # Unix timestamps, including millisecond and microsecond forms.
    if re.fullmatch(r"\d{10}(?:\.\d+)?", text):
        try:
            return dt.datetime.fromtimestamp(float(text), tz=dt.timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if re.fullmatch(r"\d{13}", text):
        try:
            return dt.datetime.fromtimestamp(int(text) / 1000, tz=dt.timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if re.fullmatch(r"\d{16}", text):
        try:
            return dt.datetime.fromtimestamp(int(text) / 1_000_000, tz=dt.timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if re.fullmatch(r"\d{8}", text):
        try:
            parsed_date = dt.datetime.strptime(text, "%Y%m%d")
            return parsed_date.replace(tzinfo=dt.timezone.utc)
        except ValueError:
            return None
    # Excel serial dates are accepted only as numeric values in the plausible date range.
    if re.fullmatch(r"\d{5}(?:\.\d+)?", text):
        try:
            serial = float(text)
            if 1 <= serial <= 100_000:
                return dt.datetime(1899, 12, 30, tzinfo=dt.timezone.utc) + dt.timedelta(days=serial)
        except (OverflowError, ValueError):
            return None

    iso_text = text.replace("Z", "+00:00")
    # Python versions vary in their acceptance of 7+ fractional-second digits.
    iso_text = re.sub(r"(\.\d{6})\d+(?=[+-]\d\d:\d\d$|$)", r"\1", iso_text)
    try:
        parsed = dt.datetime.fromisoformat(iso_text)
    except ValueError:
        parsed = None
    if parsed is not None:
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)

    try:
        parsed = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError, OverflowError):
        parsed = None
    if parsed is not None:
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    return None


def date_to_iso(value: dt.datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def date_quality(value: dt.datetime | None, as_of_date: dt.date) -> list[str]:
    if value is None:
        return []
    output: list[str] = []
    if value.date() < dt.date(2000, 1, 1):
        output.append("date_before_2000_review_only")
    if value.date() > as_of_date:
        output.append("date_after_audit_date_review_only")
    return output


def _load_salary_policy(path: Path | None) -> dict[str, Any]:
    policy: dict[str, Any] = {
        "reporting_currency": "",
        "fx_rates_to_reporting_currency": {},
        "fx_rate_date": "",
        "fx_rate_source": "",
        "annualization_factors": {},
        "status": "pending_user_approval_no_policy_file",
        "policy_file": "",
    }
    if path is None:
        return policy
    payload = json.loads(path.read_text(encoding="utf-8"))
    currency = collapse_whitespace(payload.get("reporting_currency", "")).upper()
    if currency and currency not in {"USD", "EGP", "SAR"}:
        raise ValueError("reporting_currency must be one of USD, EGP, or SAR when specified")
    rates: dict[str, float] = {}
    for raw_code, raw_rate in payload.get("fx_rates_to_reporting_currency", {}).items():
        code = collapse_whitespace(raw_code).upper()
        if code not in CURRENCY_CODES:
            raise ValueError(f"Unsupported source currency in salary policy: {raw_code!r}")
        rate = float(raw_rate)
        if not math.isfinite(rate) or rate <= 0:
            raise ValueError(f"FX rate for {code} must be finite and positive")
        rates[code] = rate
    rate_date = collapse_whitespace(payload.get("fx_rate_date", ""))
    rate_source = collapse_whitespace(payload.get("fx_rate_source", ""))
    if rates and (not currency or not rate_date or not rate_source):
        raise ValueError("FX conversion requires reporting_currency, fx_rate_date, and fx_rate_source")
    if rate_date:
        dt.date.fromisoformat(rate_date)

    factors: dict[str, float] = {}
    for raw_period, raw_factor in payload.get("annualization_factors", {}).items():
        period = collapse_whitespace(raw_period).upper()
        if period not in {"MONTH", "WEEK", "DAY", "HOUR"}:
            raise ValueError(f"Unsupported annualization period in salary policy: {raw_period!r}")
        factor = float(raw_factor)
        if not math.isfinite(factor) or factor <= 0:
            raise ValueError(f"Annualization factor for {period} must be finite and positive")
        factors[period] = factor
    policy.update({
        "reporting_currency": currency,
        "fx_rates_to_reporting_currency": rates,
        "fx_rate_date": rate_date,
        "fx_rate_source": rate_source,
        "annualization_factors": factors,
        "status": "explicit_policy_supplied",
        "policy_file": str(path),
    })
    return policy


def _build_salary_fields(
    row: Mapping[str, Any],
    source_dataset: str,
    source_file: str,
    salary_policy: Mapping[str, Any],
) -> dict[str, str]:
    salary_raw = raw_field(row, "salary", "salary_raw")
    salary_candidate, candidate_field, parsed = _salary_candidate(row)
    amounts = list(parsed.get("amounts", []))
    currency_raw = raw_field(row, "salary_currency", "currency")
    salary_currency, currency_status = detect_currency(currency_raw, salary_candidate or salary_raw)

    period_fields = [
        raw_field(row, "salary_rate"),
        raw_field(row, "salary_period"),
        raw_field(row, "pay_period"),
        raw_field(row, "salary_basis"),
    ]
    salary_period, period_status = detect_period(salary_candidate or salary_raw, period_fields, candidate_field)

    source_text = raw_field(row, "salary_source")
    sources_text = raw_field(row, "salary_sources")
    basis = raw_field(row, "salary_basis")
    fill_source = raw_field(row, "salary_fill_source")
    salary_value_type, provenance_status = _salary_value_class(
        source_dataset,
        candidate_field,
        salary_candidate,
        salary_raw,
        basis,
        source_text,
        sources_text,
        fill_source,
        amounts,
    )

    amount_1 = amounts[0] if amounts else None
    amount_2 = amounts[1] if len(amounts) > 1 else (amount_1 if amount_1 is not None else None)
    midpoint: float | None = None
    if amount_1 is not None and amount_2 is not None:
        midpoint = (amount_1 + amount_2) / 2.0
    valid_range = bool(
        amounts
        and amount_1 is not None
        and amount_2 is not None
        and amount_1 >= 0
        and amount_2 >= amount_1
    )

    annualized_min: float | None = None
    annualized_max: float | None = None
    annualized_midpoint: float | None = None
    annualization_factors = salary_policy.get("annualization_factors", {})
    if valid_range:
        if salary_period == "YEAR":
            factor = 1.0
        else:
            factor = annualization_factors.get(salary_period)
        if factor is not None:
            annualized_min = amount_1 * float(factor)
            annualized_max = amount_2 * float(factor)
            annualized_midpoint = midpoint * float(factor) if midpoint is not None else None

    reporting_currency = str(salary_policy.get("reporting_currency", "") or "")
    fx_rates = salary_policy.get("fx_rates_to_reporting_currency", {})
    fx_rate = fx_rates.get(salary_currency) if salary_currency else None
    fx_source = str(salary_policy.get("fx_rate_source", "") or "") if fx_rate else ""
    fx_date = str(salary_policy.get("fx_rate_date", "") or "") if fx_rate else ""
    converted_min = annualized_min * float(fx_rate) if annualized_min is not None and fx_rate is not None else None
    converted_max = annualized_max * float(fx_rate) if annualized_max is not None and fx_rate is not None else None

    estimate_source_url = _extract_first_url(sources_text, source_text, fill_source)
    estimate_source_date = ""  # Exact source dates are not supplied in the legacy records.
    if salary_value_type == "estimated_legacy_unverified":
        estimate_source_date_status = "source_date_not_present_in_input"
    else:
        estimate_source_date_status = "not_an_estimate_record"

    integrity: list[str] = []
    if parsed.get("status") == "range_order_reversed":
        integrity.append("salary_range_order_reversed")
    if amounts and any(value <= 0 for value in amounts):
        integrity.append("salary_amount_zero_or_negative_review")
    if amounts and salary_period in ABSOLUTE_VALUE_REVIEW_BOUNDS:
        lower_floor, upper_ceiling = ABSOLUTE_VALUE_REVIEW_BOUNDS[salary_period]
        ordered_amounts = sorted(amounts)
        if max(ordered_amounts) < lower_floor:
            integrity.append("salary_below_broad_period_screening_floor_review_only")
        if min(ordered_amounts) > upper_ceiling:
            integrity.append("salary_above_broad_period_screening_ceiling_review_only")
    if currency_status.startswith("conflict") or currency_status == "conflicting_currency_codes_in_text":
        integrity.append("salary_currency_conflict")
    if salary_value_type == "estimated_legacy_unverified":
        integrity.append("legacy_estimate_not_revalidated")
    if amounts and not salary_currency:
        integrity.append("currency_missing_or_ambiguous")
    if amounts and salary_period == "UNKNOWN":
        integrity.append("pay_period_not_stated_or_conflicting")

    scale_review_required = any(
        flag in integrity
        for flag in (
            "salary_below_broad_period_screening_floor_review_only",
            "salary_above_broad_period_screening_ceiling_review_only",
        )
    )
    if salary_value_type == "actual_reported" and valid_range and salary_currency and salary_period != "UNKNOWN" and not scale_review_required:
        statistics_eligible = True
        comparability = "reported_actual_currency_and_period_known; not FX-converted or annualized beyond identity-year"
    elif salary_value_type == "actual_reported" and scale_review_required:
        statistics_eligible = False
        comparability = "reported actual held out of salary statistics pending review of a broad period-scale flag"
    elif salary_value_type == "actual_reported" and valid_range:
        statistics_eligible = False
        comparability = "reported_actual_not_comparable_until_currency_and_pay_period_are_resolved"
    elif salary_value_type == "estimated_legacy_unverified":
        statistics_eligible = False
        comparability = "legacy estimate excluded; source-date/role/country/experience match not revalidated"
    elif salary_value_type == "not_disclosed":
        statistics_eligible = False
        comparability = "source explicitly withholds or negotiates salary"
    elif salary_value_type == "missing":
        statistics_eligible = False
        comparability = "salary missing; no imputation performed"
    elif not amounts:
        statistics_eligible = False
        comparability = "salary text could not be parsed safely"
    else:
        statistics_eligible = False
        comparability = "source provenance is not sufficient to call this an actual posted salary"

    period_output_status = period_status
    if not salary_period:
        period_output_status = "period_not_stated"
    currency_output_status = currency_status
    source_url = raw_field(row, "link", "apply_url", "source_url", "job_url")
    salary_url = estimate_source_url if salary_value_type == "estimated_legacy_unverified" else source_url

    return {
        "salary_raw": salary_raw,
        "salary_candidate_raw": salary_candidate,
        "salary_source_field_used": candidate_field,
        "salary_local_source_value": raw_field(row, "salary_local"),
        "salary_usd_source_value": raw_field(row, "salary_usd"),
        "salary_range_est_source_value": raw_field(row, "salary_range_est"),
        "salary_currency_raw": currency_raw,
        "salary_basis_raw": basis,
        "salary_rate_raw": raw_field(row, "salary_rate"),
        "salary_source_raw": source_text,
        "salary_sources_raw": sources_text,
        "salary_fill_source_raw": fill_source,
        "salary_estimate_source_url": salary_url,
        "salary_estimate_source_date": estimate_source_date,
        "salary_estimate_source_date_status": estimate_source_date_status,
        "salary_value_type": salary_value_type,
        "salary_provenance_status": provenance_status,
        "salary_parse_status": parsed.get("status", "no_salary_value"),
        "salary_amount_1_original_currency": format_number(amount_1),
        "salary_amount_2_original_currency": format_number(amount_2),
        "salary_min_original_currency": format_number(amount_1),
        "salary_max_original_currency": format_number(amount_2),
        "salary_midpoint_original_currency": format_number(midpoint),
        "salary_range_kind": parsed.get("range_kind", ""),
        "salary_currency_code": salary_currency,
        "salary_currency_detection_status": currency_output_status,
        "salary_period_code": salary_period,
        "salary_period_detection_status": period_output_status,
        "salary_annualized_min_native": format_number(annualized_min),
        "salary_annualized_max_native": format_number(annualized_max),
        "salary_annualized_midpoint_native": format_number(annualized_midpoint),
        "salary_reporting_currency": reporting_currency,
        "salary_fx_rate_to_reporting_currency": format_number(fx_rate),
        "salary_fx_rate_source": fx_source,
        "salary_fx_rate_date": fx_date,
        "salary_annualized_min_reporting_currency": format_number(converted_min),
        "salary_annualized_max_reporting_currency": format_number(converted_max),
        "salary_comparability_status": comparability,
        "salary_statistics_eligible": "yes" if statistics_eligible else "no",
        "salary_integrity_flags": ";".join(integrity),
        "salary_iqr_outlier_flag": "not_evaluated",
    }


def _experience_fields(row: Mapping[str, Any]) -> dict[str, str]:
    raw_experience = raw_field(row, "level", "years_experience", "experience")
    years_source = raw_field(row, "years_experience") or raw_field(row, "experience")
    low, high, status = parse_experience_years(years_source)
    return {
        "experience_raw": raw_experience,
        "experience_years_min": low,
        "experience_years_max": high,
        "experience_parse_status": status,
    }


def _date_fields(row: Mapping[str, Any], as_of_date: dt.date) -> dict[str, Any]:
    posted_raw, posted_key = _date_field(row, "posted_at", "job_posted_date", "date_posted")
    updated_raw, updated_key = _date_field(row, "updated", "source_updated_at")
    collected_raw, collected_key = _date_field(
        row, "collected_at", "source_collected_at", "collected_date", "date_collected",
        "scraped_at", "scraped_date", "crawl_date", "crawled_at", "ingested_at", "imported_at",
    )
    posted_parsed = parse_source_datetime(posted_raw)
    updated_parsed = parse_source_datetime(updated_raw)
    collected_parsed = parse_source_datetime(collected_raw)
    flags: list[str] = []
    flags.extend(date_quality(posted_parsed, as_of_date))
    flags.extend(f"source_updated_{value}" for value in date_quality(updated_parsed, as_of_date))
    flags.extend(f"source_collected_{value}" for value in date_quality(collected_parsed, as_of_date))
    if posted_raw and posted_parsed is None:
        flags.append("explicit_posted_date_unparseable")
    if updated_raw and updated_parsed is None:
        flags.append("source_updated_date_unparseable")
    if collected_raw and collected_parsed is None:
        flags.append("source_collection_date_unparseable")
    if not posted_raw and updated_raw:
        flags.append("updated_not_used_as_posting_date")
    if not posted_raw and not updated_raw:
        flags.append("no_posting_or_updated_date")
    return {
        "posted_at_raw": posted_raw,
        "posted_at_iso": date_to_iso(posted_parsed),
        "source_updated_at_raw": updated_raw,
        "source_updated_at_iso": date_to_iso(updated_parsed),
        "source_collected_at_raw": collected_raw,
        "source_collected_at_iso": date_to_iso(collected_parsed),
        "collection_date_field": collected_key or "not_available",
        "source_date_field": posted_key if posted_raw else (f"updated_only:{updated_key}" if updated_raw else "not_available"),
        "date_quality_flags": ";".join(flags),
        "posted_parsed": posted_parsed,
        "updated_parsed": updated_parsed,
        "collected_parsed": collected_parsed,
    }


def build_clean_record(
    row: Mapping[str, Any],
    source_file: str,
    source_dataset: str,
    bucket: str,
    row_number: int,
    skill_aliases: Mapping[str, Mapping[str, str]],
    salary_policy: Mapping[str, Any],
    as_of_date: dt.date,
    *,
    exact_duplicate: bool = False,
    duplicate_source_id_occurrence: bool = False,
    base_skill_map: Mapping[str, str] | None = None,
    base_skill_duplicate_ids: set[str] | None = None,
    base_source_available: bool = False,
) -> dict[str, str]:
    source_id = source_value(row, "id", "job_id", "row_id")
    title_raw = first_valid_raw_field(row, "title", "job_title", "job_title_short")
    title_clean = collapse_whitespace(title_raw) if source_reader.contains_source_value(title_raw) else ""
    company_raw = raw_field(row, "company", "company_name")
    company_clean = collapse_whitespace(company_raw) if source_reader.contains_source_value(company_raw) else ""
    country_raw = raw_field(row, "country", "job_country")
    country_clean = country_standardized(country_raw)
    source_url = first_valid_raw_field(row, "link", "apply_url", "source_url", "job_url")
    if not source_reader.contains_source_value(source_url):
        source_url = ""
    description = first_valid_raw_field(row, "description", "job_description", "description_text")
    if not source_reader.contains_source_value(description):
        description = ""
    raw_skills = raw_field(row, "skills", "job_skills", "required_skills")
    base_skills_raw = ""
    if source_file not in BASE_EXPORTS:
        skills_enrichment_status = "not_paired_with_base_export"
    elif not base_source_available:
        skills_enrichment_status = "base_export_unavailable"
    elif not source_id:
        skills_enrichment_status = "source_record_id_missing"
    elif source_id in (base_skill_duplicate_ids or set()):
        skills_enrichment_status = "base_source_record_id_duplicated"
    elif base_skill_map is None or source_id not in base_skill_map:
        skills_enrichment_status = "base_row_not_found"
    else:
        base_skills_raw = base_skill_map[source_id]
        skills_enrichment_status = "matches_base_export" if base_skills_raw == raw_skills else "changed_vs_base_export"
    raw_tokens = source_reader.split_skill_labels(raw_skills, source_file, deduplicate=False)
    unique_tokens = source_reader.ordered_unique_skills(raw_tokens)

    unique_skill_ids: list[str] = []
    seen_skill_ids: set[str] = set()
    for token in unique_tokens:
        metadata = source_reader.resolve_skill_metadata(token, skill_aliases)
        skill_id = metadata["skill_id"]
        if skill_id not in seen_skill_ids:
            seen_skill_ids.add(skill_id)
            unique_skill_ids.append(skill_id)

    date_fields = _date_fields(row, as_of_date)
    salary_fields = _build_salary_fields(row, source_dataset, source_file, salary_policy)
    experience_fields = _experience_fields(row)
    flags: list[str] = []

    mapped_values = {
        "title": title_clean,
        "company": company_clean,
        "country": country_clean,
        "description": description,
        "source_url": source_url,
        "skills": raw_skills,
    }
    flags.extend(
        f"missing_{field}"
        for field, value in mapped_values.items()
        if not source_reader.contains_source_value(value)
    )
    if source_reader.contains_source_value(title_raw) and title_raw != title_clean:
        flags.append("title_whitespace_normalized_in_derived_field")
    if source_reader.contains_source_value(country_raw) and country_raw != country_clean:
        flags.append("country_alias_or_whitespace_normalized_in_derived_field")
    if salary_fields["salary_value_type"] == "missing":
        flags.append("missing_salary_no_imputation")
    elif salary_fields["salary_value_type"] == "not_disclosed":
        flags.append("salary_not_disclosed_in_source")
    elif salary_fields["salary_value_type"] == "estimated_legacy_unverified":
        flags.append("legacy_estimate_preserved_but_excluded_from_actual_statistics")
    if exact_duplicate:
        flags.append("exact_duplicate_within_source_retained")
    if duplicate_source_id_occurrence:
        flags.append("duplicate_source_record_id_occurrence_retained")
    if date_fields["date_quality_flags"]:
        flags.extend(date_fields["date_quality_flags"].split(";"))
    if salary_fields["salary_integrity_flags"]:
        flags.extend(salary_fields["salary_integrity_flags"].split(";"))
    if source_url:
        parsed_url = urlparse(source_url)
        url_status = "syntactically_valid_http_url" if parsed_url.scheme in {"http", "https"} and parsed_url.netloc else "invalid_or_non_http_url"
        if url_status != "syntactically_valid_http_url":
            flags.append("source_url_invalid_syntax_or_scheme")
    else:
        url_status = "missing"

    searchable_text = " ".join((title_raw, company_raw, country_raw, raw_skills, description, salary_fields["salary_raw"]))
    mojibake = bool(MOJIBAKE_PATTERN.search(searchable_text))
    if mojibake:
        flags.append("possible_mojibake_preserved_for_review")

    platform = raw_field(row, "source", "platform", "job_via")
    if platform.casefold().startswith("via "):
        platform = platform[4:]
    source_row = {str(key): "" if value is None else str(value) for key, value in row.items()}
    identifier_material = source_id or f"row-{row_number}"
    row_digest = hashlib.sha256(
        json.dumps(source_row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    record_id = f"{source_dataset}:{identifier_material}:row-{row_number}:{row_digest}"

    fields: dict[str, str] = {
        "record_id": record_id,
        "source_dataset": source_dataset,
        "source_file": source_file,
        "source_row_number": str(row_number),
        "source_record_id": source_id,
        "source_record_id_duplicate_occurrence": "yes" if duplicate_source_id_occurrence else "no",
        "record_origin": raw_field(row, "record_origin", "source_file"),
        "source_platform": platform,
        "title_raw": title_raw,
        "title_clean": title_clean,
        "title_key": title_clean.casefold(),
        "company_raw": company_raw,
        "company_clean": company_clean,
        "country_raw": country_raw,
        "country_standardized": country_clean,
        "location_scope": country_location_scope(country_clean),
        "city_raw": raw_field(row, "city"),
        "region_raw": raw_field(row, "state_region", "region", "state"),
        "location_raw": raw_field(row, "location_raw", "job_location", "job_location_raw"),
        "work_mode_raw": raw_field(row, "work_mode", "work_arrangement"),
        "remote_flag_raw": raw_field(row, "job_work_from_home"),
        "employment_type_raw": raw_field(row, "job_type", "job_schedule_type", "employment_type"),
        "category_raw": raw_field(row, "category", "job_category", "sub_category", "job_track"),
        "description_raw": description,
        "description_char_count": str(len(description)),
        "skills_raw": raw_skills,
        "skills_base_raw": base_skills_raw,
        "skills_tokens_json": json.dumps(unique_tokens, ensure_ascii=False, separators=(",", ":")),
        "skill_ids_json": json.dumps(unique_skill_ids, ensure_ascii=False, separators=(",", ":")),
        "skill_token_count_raw": str(len(raw_tokens)),
        "skill_token_count_unique": str(len(unique_tokens)),
        "skill_canonical_id_count": str(len(unique_skill_ids)),
        "skill_duplicate_token_count": str(max(0, len(raw_tokens) - len(unique_tokens))),
        "skills_source_raw": raw_field(row, "skills_source"),
        "skills_enrichment_status": skills_enrichment_status,
        "source_url_raw": source_url,
        "source_url_syntax_status": url_status,
        "listing_status": "unknown_not_verified",
        "snapshot_type": bucket,
        "exact_duplicate_within_source": "yes" if exact_duplicate else "no",
        "encoding_suspected_mojibake": "yes" if mojibake else "no",
        "data_quality_flags": ";".join(dict.fromkeys(flag for flag in flags if flag)),
        "source_row_json": json.dumps(source_row, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
    }
    fields.update(experience_fields)
    fields.update({key: value for key, value in date_fields.items() if key in {
        "posted_at_raw", "posted_at_iso", "source_updated_at_raw", "source_updated_at_iso",
        "source_collected_at_raw", "source_collected_at_iso", "collection_date_field",
        "source_date_field", "date_quality_flags"
    }})
    fields.update(salary_fields)
    # Rebuild flags after all source-level salary/date fields have been added.
    final_flags = [item for item in fields["data_quality_flags"].split(";") if item]
    fields["data_quality_flags"] = ";".join(dict.fromkeys(final_flags))
    return {field: fields.get(field, "") for field in INTERMEDIATE_FIELDS}


def _iter_source_rows(path: Path, kind: str) -> Iterator[dict[str, str]]:
    if kind == "xlsx":
        yield from source_reader.read_excel_workbook_rows(path)
        return
    with source_reader.open_comma_separated_values_reader(path) as reader:
        yield from reader


@contextmanager
def _open_source_rows(path: Path, kind: str) -> Iterator[Iterable[dict[str, str]]]:
    if kind == "xlsx":
        yield source_reader.read_excel_workbook_rows(path)
        return
    with source_reader.open_comma_separated_values_reader(path) as reader:
        yield reader


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_manifest(raw_directory: Path) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    job_specs = {spec["file"]: spec for spec in JOB_SOURCE_SPECS}
    for filename in ALL_EXPECTED_FILES:
        path = raw_directory / filename
        spec = job_specs.get(filename)
        reference_only = filename in REFERENCE_ONLY_FILES
        if path.is_file():
            manifest.append({
                "file": filename,
                "role": "base_skill_comparison_only" if reference_only else "selected_job_source",
                "required_for_full_scope": bool(spec.get("required")) if spec else False,
                "exists": True,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "status": "available",
            })
        else:
            manifest.append({
                "file": filename,
                "role": "base_skill_comparison_only" if reference_only else "selected_job_source",
                "required_for_full_scope": bool(spec.get("required")) if spec else False,
                "exists": False,
                "size_bytes": 0,
                "sha256": "",
                "status": "missing_required_source" if spec and spec.get("required") else "missing_reference_source",
            })
    return manifest


def _csv_writer(path: Path, fieldnames: list[str]) -> tuple[Any, csv.DictWriter]:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = gzip.open(path, "wt", encoding="utf-8", newline="", compresslevel=6) if path.suffix == ".gz" else path.open("w", encoding="utf-8", newline="")
    writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    return handle, writer


def _write_plain_csv(path: Path, fieldnames: list[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _metric_value(row: Mapping[str, Any], metric: str) -> bool:
    if metric == "title":
        return bool(source_value(row, "title", "job_title", "job_title_short"))
    if metric == "company":
        return bool(source_value(row, "company", "company_name"))
    if metric == "country":
        return bool(source_value(row, "country", "job_country"))
    if metric == "description":
        return bool(source_value(row, "description", "job_description", "description_text"))
    if metric == "source_url":
        return bool(source_value(row, "link", "apply_url", "source_url", "job_url"))
    if metric == "skills":
        return bool(source_value(row, "skills", "job_skills", "required_skills"))
    if metric == "salary_raw_numeric":
        return source_reader.contains_numeric_salary_amount(raw_field(row, "salary", "salary_raw"))
    if metric == "salary_any_numeric_source":
        values = [raw_field(row, key) for key in (
            "salary", "salary_raw", "salary_range_est", "salary_local", "salary_usd", "salary_year_avg", "salary_hour_avg"
        )]
        return any(source_reader.contains_numeric_salary_amount(value) for value in values)
    if metric == "explicit_posted_date":
        return bool(source_value(row, "posted_at", "job_posted_date", "date_posted"))
    if metric == "source_updated_at":
        return bool(source_value(row, "updated", "source_updated_at"))
    if metric == "source_collection_date":
        return bool(source_value(row, "collected_at", "source_collected_at", "collected_date", "date_collected", "scraped_at", "scraped_date", "crawl_date", "crawled_at", "ingested_at", "imported_at"))
    raise KeyError(metric)


def _coverage_dict(total: int, counts: Mapping[str, int]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in PRE_QUALITY_FIELDS:
        present = int(counts.get(field, 0))
        missing = total - present
        result[field] = {
            "present": present,
            "missing": missing,
            "missing_rate": round(missing / total, 6) if total else None,
        }
    return result


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("quantile requires at least one value")
    position = (len(ordered) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _salary_group_key(record: Mapping[str, str]) -> tuple[str, str, str, str]:
    return (
        record.get("country_standardized", ""),
        record.get("title_key", ""),
        record.get("salary_currency_code", ""),
        record.get("salary_period_code", ""),
    )


def _load_skill_reference() -> dict[str, dict[str, str]]:
    path = source_reader.SKILL_CURATION_FILE_PATH
    if path.is_file():
        return source_reader.load_skill_aliases(path)
    return {}


def _load_base_skill_map(path: Path) -> tuple[dict[str, str], set[str]]:
    values: dict[str, list[str]] = defaultdict(list)
    with _open_source_rows(path, "csv") as rows:
        for row in rows:
            identifier = source_value(row, "id", "job_id", "row_id")
            if identifier:
                values[identifier].append(raw_field(row, "skills", "job_skills", "required_skills"))
    duplicates = {identifier for identifier, entries in values.items() if len(entries) > 1}
    unique = {identifier: entries[0] for identifier, entries in values.items() if len(entries) == 1}
    return unique, duplicates


def _audit_base_pairs(raw_directory: Path) -> dict[str, Any]:
    reports: dict[str, Any] = {}
    for enriched_name, base_name in BASE_EXPORTS.items():
        base_path = raw_directory / base_name
        enriched_path = raw_directory / enriched_name
        result: dict[str, Any] = {
            "base_file": base_name,
            "enriched_file": enriched_name,
            "available": base_path.is_file() and enriched_path.is_file(),
            "base_rows": 0,
            "enriched_rows": 0,
            "base_unique_ids": 0,
            "enriched_unique_ids": 0,
            "base_duplicate_id_occurrences": 0,
            "enriched_duplicate_id_occurrences": 0,
            "ids_only_in_base": 0,
            "ids_only_in_enriched": 0,
            "matched_ids": 0,
            "matched_ids_with_changed_skills": 0,
            "skill_values_filled_from_empty": 0,
            "source_record_id_missing_rows": 0,
        }
        if not result["available"]:
            result["status"] = "pair_comparison_unavailable"
            reports[enriched_name] = result
            continue

        def collect(path: Path) -> tuple[dict[str, Counter[str]], int, int, int]:
            values: dict[str, Counter[str]] = defaultdict(Counter)
            total = 0
            missing_ids = 0
            duplicate_occurrences = 0
            with _open_source_rows(path, "csv") as rows:
                for row in rows:
                    total += 1
                    identifier = source_value(row, "id", "job_id", "row_id")
                    if not identifier:
                        missing_ids += 1
                        identifier = f"__row_without_id__:{total}"
                    if values[identifier]:
                        duplicate_occurrences += 1
                    skills = raw_field(row, "skills", "job_skills", "required_skills")
                    values[identifier][skills] += 1
            return values, total, missing_ids, duplicate_occurrences

        base_values, base_total, base_missing, base_dupes = collect(base_path)
        enriched_values, enriched_total, enriched_missing, enriched_dupes = collect(enriched_path)
        base_ids, enriched_ids = set(base_values), set(enriched_values)
        matched = base_ids & enriched_ids
        changed = [identifier for identifier in matched if base_values[identifier] != enriched_values[identifier]]
        filled = 0
        for identifier in changed:
            base_nonempty = sum(count for skill, count in base_values[identifier].items() if skill.strip())
            enriched_nonempty = sum(count for skill, count in enriched_values[identifier].items() if skill.strip())
            if base_nonempty == 0 and enriched_nonempty > 0:
                filled += min(sum(base_values[identifier].values()), sum(enriched_values[identifier].values()))

        result.update({
            "base_rows": base_total,
            "enriched_rows": enriched_total,
            "base_unique_ids": len(base_ids),
            "enriched_unique_ids": len(enriched_ids),
            "base_duplicate_id_occurrences": base_dupes,
            "enriched_duplicate_id_occurrences": enriched_dupes,
            "ids_only_in_base": len(base_ids - enriched_ids),
            "ids_only_in_enriched": len(enriched_ids - base_ids),
            "matched_ids": len(matched),
            "matched_ids_with_changed_skills": len(changed),
            "skill_values_filled_from_empty": filled,
            "source_record_id_missing_rows": base_missing + enriched_missing,
            "status": "row_counts_and_id_sets_match" if base_total == enriched_total and base_ids == enriched_ids else "row_or_id_mismatch_review",
        })
        reports[enriched_name] = result
    return reports


def _write_manifest(path: Path, manifest: list[dict[str, Any]], source_ref: str) -> None:
    rows = [{**item, "source_ref": source_ref} for item in manifest]
    _write_plain_csv(path, ["file", "role", "required_for_full_scope", "exists", "size_bytes", "sha256", "status", "source_ref"], rows)


def _stats_rows(
    group_points: Mapping[tuple[str, str, str, str], list[tuple[float, float, float, str]]],
    outlier_counts: Mapping[tuple[str, str, str, str], int],
    display_titles: Mapping[tuple[str, str], Counter[str]],
    files_by_group: Mapping[tuple[str, str, str, str], set[str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in sorted(group_points, key=lambda item: (item[0].casefold(), item[1], item[2], item[3])):
        country, title_key, currency, period = key
        points = group_points[key]
        midpoints = [item[0] for item in points]
        lower_values = [item[1] for item in points]
        upper_values = [item[2] for item in points]
        title_counts = display_titles.get((country, title_key), Counter())
        title_display = sorted(title_counts, key=lambda value: (-title_counts[value], value.casefold()))[0] if title_counts else title_key
        rows.append({
            "country": country,
            "title_display": title_display,
            "title_key": title_key,
            "salary_currency_code": currency,
            "salary_period_code": period,
            "actual_record_count": len(points),
            "estimated_record_count": 0,
            "average_of_record_midpoints_native": format_number(statistics.fmean(midpoints)),
            "median_of_record_midpoints_native": format_number(statistics.median(midpoints)),
            "minimum_reported_lower_bound_native": format_number(min(lower_values)),
            "maximum_reported_upper_bound_native": format_number(max(upper_values)),
            "minimum_record_midpoint_native": format_number(min(midpoints)),
            "maximum_record_midpoint_native": format_number(max(midpoints)),
            "potential_iqr_outlier_records_included": int(outlier_counts.get(key, 0)),
            "source_files": ";".join(sorted(files_by_group.get(key, set()))),
            "statistics_scope": "actual_reported_only; exact title/country/currency/pay-period group; midpoint is arithmetic midpoint of the posted range",
            "fx_conversion_applied": "no; statistics remain in source currency and period",
        })
    return rows


def _write_profile_outputs(
    report_directory: Path,
    role_country: Mapping[tuple[str, str], Counter[str]],
    country_counts: Mapping[str, Counter[str]],
    skill_counts: Mapping[str, Counter[str]],
    estimate_sources: Mapping[tuple[str, str, str, str, str, str], Counter[str]],
    salary_policy: Mapping[str, Any],
) -> dict[str, str]:
    role_rows: list[dict[str, Any]] = []
    for country, title_key in sorted(role_country, key=lambda item: (item[0].casefold(), item[1])):
        counts = role_country[(country, title_key)]
        role_rows.append({"country": country, "title_key": title_key, **counts})
    role_path = report_directory / "salary_coverage_by_role_country.csv"
    _write_plain_csv(role_path, [
        "country", "title_key", "total_job_records", "actual_reported_records", "actual_statistics_eligible_records",
        "estimated_legacy_unverified_records", "source_reported_unverified_records", "not_disclosed_records",
        "missing_salary_records", "unparseable_salary_records", "records_without_currency_or_period",
    ], role_rows)

    country_rows: list[dict[str, Any]] = []
    for country in sorted(country_counts, key=lambda value: value.casefold()):
        counts = country_counts[country]
        country_rows.append({"country_or_scope": country, **counts})
    country_path = report_directory / "country_profile.csv"
    _write_plain_csv(country_path, [
        "country_or_scope", "job_records", "distinct_title_keys", "actual_reported_salary_records",
        "actual_statistics_eligible_records", "estimated_legacy_unverified_records", "missing_salary_records",
    ], country_rows)

    skill_rows: list[dict[str, Any]] = []
    for skill_id in sorted(skill_counts, key=lambda value: (-skill_counts[value]["job_record_count"], value)):
        skill_rows.append({"skill_id": skill_id, **skill_counts[skill_id]})
    skill_path = report_directory / "skill_profile.csv"
    _write_plain_csv(skill_path, [
        "skill_id", "skill_label", "skill_category", "skill_match_policy", "skill_review_status",
        "job_record_count", "raw_token_occurrences", "source_datasets",
    ], skill_rows)

    estimate_rows: list[dict[str, Any]] = []
    for key in sorted(estimate_sources, key=lambda item: (item[0], item[1], item[2], item[3], item[4], item[5])):
        dataset, source_text, sources_text, fill_source, basis, currency = key
        counts = estimate_sources[key]
        estimate_rows.append({
            "source_dataset": dataset,
            "salary_source_raw": source_text,
            "salary_sources_raw": sources_text,
            "salary_fill_source_raw": fill_source,
            "salary_basis_raw": basis,
            "source_currency_label": currency,
            "legacy_estimate_record_count": counts["rows"],
            "source_date_available_record_count": 0,
            "status": "preserved_not_revalidated_not_used_for_salary_statistics",
            "review_note": "Original source text/URL is retained; no estimate was added or approved by this run.",
        })
    estimate_path = report_directory / "legacy_salary_estimate_inventory.csv"
    _write_plain_csv(estimate_path, [
        "source_dataset", "salary_source_raw", "salary_sources_raw", "salary_fill_source_raw", "salary_basis_raw",
        "source_currency_label", "legacy_estimate_record_count", "source_date_available_record_count", "status", "review_note",
    ], estimate_rows)
    return {
        "salary_coverage_by_role_country": str(role_path),
        "country_profile": str(country_path),
        "skill_profile": str(skill_path),
        "legacy_salary_estimate_inventory": str(estimate_path),
    }


def _sqlite_round_trip_check(
    dataset_path: Path,
    expected_stats: list[dict[str, Any]],
) -> dict[str, Any]:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """CREATE TABLE salary_rows (
            record_id TEXT PRIMARY KEY,
            country TEXT NOT NULL,
            title_key TEXT NOT NULL,
            currency TEXT NOT NULL,
            pay_period TEXT NOT NULL,
            midpoint REAL NOT NULL,
            lower_bound REAL NOT NULL,
            upper_bound REAL NOT NULL
        )"""
    )
    eligible_count = 0
    dataset_count = 0
    with gzip.open(dataset_path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for record in reader:
            dataset_count += 1
            if record.get("salary_statistics_eligible") != "yes":
                continue
            midpoint = float(record["salary_midpoint_original_currency"])
            low = float(record["salary_min_original_currency"])
            high = float(record["salary_max_original_currency"])
            connection.execute(
                "INSERT INTO salary_rows VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record["record_id"],
                    record["country_standardized"],
                    record["title_key"],
                    record["salary_currency_code"],
                    record["salary_period_code"],
                    midpoint,
                    low,
                    high,
                ),
            )
            eligible_count += 1
    sql_groups = connection.execute(
        """SELECT country, title_key, currency, pay_period, COUNT(*), AVG(midpoint), MIN(lower_bound), MAX(upper_bound)
           FROM salary_rows GROUP BY country, title_key, currency, pay_period"""
    ).fetchall()
    expected_by_key = {
        (row["country"], row["title_key"], row["salary_currency_code"], row["salary_period_code"]): row
        for row in expected_stats
    }
    compared = 0
    mismatches: list[str] = []
    for country, title, currency, period, count, average, low, high in sql_groups:
        expected = expected_by_key.get((country, title, currency, period))
        if expected is None:
            mismatches.append(f"unexpected SQLite group: {country}/{title}/{currency}/{period}")
            continue
        compared += 1
        if int(expected["actual_record_count"]) != count:
            mismatches.append(f"row count mismatch: {country}/{title}/{currency}/{period}")
        if not math.isclose(float(expected["average_of_record_midpoints_native"]), average, rel_tol=1e-9, abs_tol=1e-7):
            mismatches.append(f"average mismatch: {country}/{title}/{currency}/{period}")
        if not math.isclose(float(expected["minimum_reported_lower_bound_native"]), low, rel_tol=1e-9, abs_tol=1e-7):
            mismatches.append(f"minimum mismatch: {country}/{title}/{currency}/{period}")
        if not math.isclose(float(expected["maximum_reported_upper_bound_native"]), high, rel_tol=1e-9, abs_tol=1e-7):
            mismatches.append(f"maximum mismatch: {country}/{title}/{currency}/{period}")
    if compared != len(expected_by_key):
        mismatches.append(f"group count mismatch: SQLite {compared}, report {len(expected_by_key)}")
    connection.close()
    return {
        "status": "passed" if not mismatches else "failed",
        "dataset_rows_read": dataset_count,
        "eligible_salary_rows_loaded": eligible_count,
        "salary_groups_compared": compared,
        "mismatches": mismatches,
        "scope_note": "in-memory SQLite round-trip of the final CSV and salary aggregates; not a comparison to the missing project job_market.sqlite3 database",
    }


def _workspace_path_label(path: Path | str) -> str:
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return candidate.as_posix()


def _markdown_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _write_markdown_report(
    path: Path,
    summary: Mapping[str, Any],
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    per_file: Mapping[str, Any],
    salary_stats: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    missing_sources = summary.get("missing_required_sources", [])
    before_cov = before.get("field_coverage", {})
    after_cov = after.get("field_coverage", {})
    lines = [
        "# التقرير النهائي لجودة البيانات والتنظيف",
        "",
        f"- **تاريخ التدقيق:** {summary.get('audit_date', '')}",
        f"- **مرجع المصادر:** `{summary.get('source_ref', '')}`",
        f"- **الملف النهائي:** `{summary.get('cleaned_dataset_path', '')}`",
        f"- **مرجع المدخلات:** `{summary.get('raw_data_directory', '')}`",
        "",
        "## النطاق والقيود",
        "",
        f"تم تنظيف **{summary.get('output_rows', 0):,}** سجلًا من {summary.get('available_job_source_count', 0)} ملفات مصدر متاحة. احتُفظ بكل صف؛ عدد الصفوف المحذوفة أو المستبعدة هو **0**، والتكرارات الدقيقة موسومة وليست محذوفة.",
        "",
    ]
    if missing_sources:
        lines.append("المصدر التاريخي/الإلزامي التالي غير موجود في نسخة `main` التي دُققت؛ لذلك هذه نتيجة جزئية وليست إعادة تنظيف كاملة لكل أرشيف المشروع:")
        lines.append("")
        lines.extend(f"- `{filename}`" for filename in missing_sources)
        lines.append("")
    lines.extend([
        "### جرد المصادر المستخدمة",
        "",
        "| الملف | الصفوف | راتب رقمي قبل التنظيف | قيمة راتب محللة بعده | راتب Actual | تقدير موروث | تكرار دقيق محفوظ |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for filename, source in per_file.items():
        rows = int(source.get("rows", 0))
        if rows == 0:
            continue
        before_fields = source.get("missing_fields_before", {})
        after_fields = source.get("missing_fields_after", {})
        value_types = source.get("salary_value_type_counts", {})
        numeric_after = rows - int(after_fields.get("salary_numeric_parsed", rows))
        lines.append(
            f"| `{_markdown_cell(filename)}` | {rows:,} | {rows - int(before_fields.get('salary_any_numeric_source', rows)):,} | {numeric_after:,} | {int(value_types.get('actual_reported', 0)):,} | {int(value_types.get('estimated_legacy_unverified', 0)):,} | {int(source.get('exact_duplicate_occurrences_retained', 0)):,} |"
        )
    lines.extend([
        "",
        "لا توجد قاعدة `job_market.sqlite3` أو حزمة Parquet المعتمدة في مساحة العمل الحالية. أُعيدت تحليلات التغطية والرواتب على الملف المنظّف المتاح، وأُجري اختبار إدخال/تجميع منفصل داخل SQLite بالذاكرة. هذا الاختبار ليس مقارنة بقاعدة المشروع التاريخية.",
        "",
        "## قبل التنظيف وبعده",
        "",
        "القيم الخام محفوظة داخل `source_row_json` والحقول الخام ذات الصلة. المقارنة أدناه تقيس التغطية؛ التنظيف لا يملأ بيانات ناقصة ولا يحذف صفوفًا.",
        "",
        "| الحقل/الفحص | قبل التنظيف: متاح | بعد التنظيف: متاح | ملاحظة |",
        "|---|---:|---:|---|",
    ])
    mapping = [
        ("المسمى الوظيفي", "title", "title_clean", "تنظيف المسافات فقط؛ لا دمج دلاليًا بين المسميات."),
        ("الشركة", "company", "company_clean", "تطبيع مسافات في العمود المشتق فقط."),
        ("الدولة/النطاق", "country", "country_standardized", "أسماء شائعة موحدة بقواعد صريحة؛ Remote/Worldwide ليست دولة."),
        ("الوصف", "description", "description_raw", "النص الأصلي محفوظ بلا إعادة صياغة."),
        ("رابط المصدر", "source_url", "source_url_raw", "تحقق شكلي فقط، دون طلب الشبكة."),
        ("المهارات", "skills", "skills_raw", "النص الأصلي محفوظ؛ أضيفت قائمة رموز منظّمة مع إزالة تكرار الرمز داخل الصف."),
        ("نص راتب رقمي", "salary_raw_numeric", "salary_numeric_parsed", "القيم التقديرية الموروثة مفصولة عن الرواتب المنشورة."),
        ("تاريخ نشر صريح", "explicit_posted_date", "posted_date_parsed", "لم يُحوّل updated إلى تاريخ نشر."),
        ("حقل updated", "source_updated_at", "source_updated_at_parsed", "تاريخ مصدر محفوظ منفصلًا؛ دلالته غير مؤكدة."),
    ]
    for label, before_key, after_key, note in mapping:
        b = before_cov.get(before_key, {})
        a = after_cov.get(after_key, {})
        lines.append(f"| {label} | {b.get('present', 0):,} | {a.get('present', 0):,} | {note} |")
    lines.extend([
        "",
        f"- الصفوف قبل/بعد: **{summary.get('input_rows', 0):,} / {summary.get('output_rows', 0):,}**.",
        f"- تكرارات الصفوف الدقيقة داخل المصدر، محفوظة ومعلّمة: **{summary.get('exact_duplicate_occurrences_retained', 0):,}**.",
        f"- سجلات فيها نصوص يُحتمل أنها مشوّهة الترميز: **{after.get('possible_mojibake_records', 0):,}**؛ لم تُصحح آليًا لتجنب تغيير النص دون مرجع.",
        f"- تواريخ قديمة جدًا أو بعد تاريخ التدقيق الموسومة للمراجعة: **{after.get('date_out_of_expected_range_records', 0):,}**؛ لم تُحذف.",
        f"- قيم الدولة التي كانت نصًا موجودًا قبل التنظيف ثم صُنفت كـplaceholder مفقود بعده: **{max(0, before_cov.get('country', {}).get('present', 0) - after_cov.get('country_standardized', {}).get('present', 0)):,}**؛ بقيت القيم الخام في `country_raw` و`source_row_json`.",
        "",
        "## سياسة الرواتب ونتائجها",
        "",
        "- بقي `salary_raw` وكل حقول الرواتب الأصلية كما وردت، بما فيها `salary_local` و`salary_usd` و`salary_range_est` ومراجعها. لم تُستبدل القيم الأصلية.",
        "- لم تُضف تقديرات جديدة ولم تُملأ الرواتب المفقودة. التقديرات القديمة الموجودة في المصدر وُسمت `estimated_legacy_unverified`، وحُفظت مراجعها، لكنها استُبعدت من إحصاءات الرواتب الفعلية لأن تاريخ المصدر/ملاءمة المسمى والدولة ومستوى الخبرة غير مثبتة لكل سجل.",
        "- الراتب المعلن من ملف إعلان وظيفي موسوم `actual_reported`، أي مبلغ ورد في ملف المصدر، وليس تحققًا حيًا من الإعلان. القيم التي لا تثبت أنها إعلان فعلي تبقى `source_reported_unverified`.",
        "- لم يُحسم بعد اختيار عملة التقرير ولا سعر الصرف/مرجعه وتاريخه، كما لم تُعتمد عوامل تحويل الساعة/اليوم/الأسبوع/الشهر إلى سنة. لذلك لم يحدث تحويل بين العملات، ولم تُسنون الفترات غير السنوية. أُبقيت القيمة السنوية المصدرية كما هي فقط عندما كانت الفترة `YEAR` صريحة.",
        "- تُجمع الإحصاءات حسب المسمى النصي المطبع بدقة، والدولة/النطاق، والعملة الصريحة، وفترة الدفع الصريحة. لا تُخلط العملات أو الفترات. متوسط/وسيط الراتب يمثلان منتصف النطاق المعلن لكل سجل، مع بقاء حدود النطاق متاحة في CSV.",
        "",
        "### تغطية الرواتب",
        "",
        f"- أرقام قابلة للتحليل كقيم راتب: **{summary.get('salary', {}).get('numeric_parseable_records', 0):,}**.",
        f"- رواتب مصدرية مصنفة `actual_reported`: **{summary.get('salary', {}).get('actual_reported_records', 0):,}**.",
        f"- منها مجموعات قابلة لإحصاءات منفصلة بعملة وفترة صريحتين: **{summary.get('salary', {}).get('actual_statistics_eligible_records', 0):,}** في **{len(salary_stats):,}** مجموعة مسمى/دولة/عملة/فترة.",
        f"- تقديرات سابقة غير متحققة بقيت في المصدر: **{summary.get('salary', {}).get('legacy_estimate_unverified_records', 0):,}**؛ لا تدخل في إحصاءات الرواتب الفعلية.",
        f"- سجلات راتب بلا عملة صريحة أو مع تعارض في العملة: **{summary.get('salary', {}).get('currency_missing_or_conflict_records', 0):,}**.",
        f"- سجلات راتب لا تحدد فترة الدفع: **{summary.get('salary', {}).get('period_unknown_records', 0):,}**.",
        f"- رواتب مفقودة بلا تعويض أو تخمين: **{summary.get('salary', {}).get('missing_records', 0):,}**.",
        f"- سجلات راتب تحتاج مراجعة صفية قبل استخدامها (مصدر غير مؤكد، عملة/فترة غير محسومة، أو نص غير قابل للتحليل): **{summary.get('salary', {}).get('review_candidate_records', 0):,}**؛ التفاصيل في `salary_review_candidates.csv`.",
        f"- قيم موسومة بحدود الفرز الواسعة حسب فترة الدفع: **{summary.get('salary', {}).get('absolute_scale_review_records', 0):,}**؛ تبقى سجلاتها محفوظة، وتُستبعد مؤقتًا من إحصاءات الرواتب إلى حين المراجعة. التفاصيل في `salary_review_candidates.csv`.",
        "",
        "### أبرز مجموعات الرواتب الفعلية المؤهلة",
        "",
        "الأرقام التالية لا تخلط بين عملات أو فترات. قد تكون المجموعة صغيرة؛ راجع `actual_record_count` قبل عرضها في لوحة المعلومات.",
        "",
        "| الدولة/النطاق | المسمى | العملة | الفترة | عدد السجلات | متوسط منتصف النطاق | وسيط منتصف النطاق | أقل حد منشور | أعلى حد منشور |",
        "|---|---|---|---|---:|---:|---:|---:|---:|",
    ])
    for row in sorted(salary_stats, key=lambda item: (-int(item["actual_record_count"]), item["country"], item["title_key"]))[:15]:
        lines.append(
            f"| {_markdown_cell(row['country'])} | {_markdown_cell(row['title_display'])} | {row['salary_currency_code']} | {row['salary_period_code']} | {row['actual_record_count']} | {row['average_of_record_midpoints_native']} | {row['median_of_record_midpoints_native']} | {row['minimum_reported_lower_bound_native']} | {row['maximum_reported_upper_bound_native']} |"
        )
    if not salary_stats:
        lines.append("| — | لا توجد سجلات تستوفي شروط المقارنة حاليًا | — | — | 0 | — | — | — | — |")
    lines.extend([
        "",
        "## قواعد التنظيف والاختبارات",
        "",
        "1. الاحتفاظ بكل صف وتسجيل الملف/رقم الصف/معرّف المصدر وبصمة الملف؛ لا إزالة للتكرارات ولا دمج بين مصادر مختلفة.",
        "2. حفظ الصف الخام كاملًا في `source_row_json`. تنظيف المسافات والتوحيد اللغوي محصور في الأعمدة المشتقة، من دون توحيد تقريبي لعناوين الوظائف.",
        "3. تحليل التواريخ من الحقول الصريحة فقط. `updated` محفوظ ومحلل منفصلًا، ولا يتحول إلى `posted_at`.",
        "4. تفسير رموز الرواتب والعملات والفترات فقط عند وجود دليل نصي أو عمود مصدر صريح. رمز `$` وحده يظل ملتبسًا ولا يُحسم من الدولة.",
        "5. تنبيه القيم الصفرية/السالبة، وترتيب النطاق المعكوس، وتعارض العملة، والقيم الشاذة بطريقة IQR داخل مجموعات متجانسة عند توفر 8 سجلات على الأقل. توجد أيضًا حدود واسعة لكل فترة دفع لفرز القيم شديدة الانخفاض/الارتفاع. السجل الموسوم يبقى محفوظًا ولا يُصحح أو يُحذف، لكن تُحجب قيمته مؤقتًا عن إحصاءات الرواتب إلى أن تُراجع.",
        "6. اختبار تطابق عدد الصفوف وهوية السجلات، وسلامة بصمات الملفات الخام، واختبار تجميع SQLite بالذاكرة مقابل جداول الإحصاء.",
        "",
        "## التحقق من قاعدة البيانات والتحليل",
        "",
        f"- فحص SQLite بالذاكرة: **{summary.get('sqlite_round_trip', {}).get('status', 'غير متاح')}**؛ {summary.get('sqlite_round_trip', {}).get('eligible_salary_rows_loaded', 0):,} سجل راتب مؤهل و{summary.get('sqlite_round_trip', {}).get('salary_groups_compared', 0):,} مجموعة جرى التحقق منها.",
        f"- قاعدة المشروع الموجودة مسبقًا: **{summary.get('existing_database_status', 'غير متحقق')}**.",
        f"- إعادة تشغيل تحليل الأرشيف الكامل: **{summary.get('full_archive_analysis_status', 'غير متاح')}**.",
        ("- أُعيد حساب تغطية الدول والمسميات والمهارات وإحصاءات الرواتب المؤهلة من جميع مصادر الوظائف المعلنة المتاحة لهذا التشغيل؛ لا يثبت ذلك أن الإعلانات ما زالت نشطة." if not missing_sources else "- أُعيد حساب تغطية الدول والمسميات والمهارات وإحصاءات الرواتب المؤهلة من الملفات المتاحة فقط. لا تمثل هذه المجموعة الجزئية كامل أرشيف الوظائف، ولا تثبت أن الإعلانات ما زالت نشطة."),
        "",
        "## الملفات الناتجة",
        "",
    ])
    for label, location in summary.get("deliverables", {}).items():
        lines.append(f"- **{label}:** `{location}`")
    lines.extend([
        "",
        "## ما لم يُحسم / ما يحتاج متابعة",
        "",
        ("- لم تبقَ مصادر وظائف معلنة ناقصة. تظل قاعدة SQLite وحزمة Parquet المعتمدة غير متاحتين للمقارنة وإعادة إنتاج التحليل التاريخي المرتبط بهما." if not missing_sources else "- استعادة مصادر الوظائف المفقودة، ومنها `International_Tech_Jobs_Filtered.csv` عند غيابها، والأرشيف/قاعدة SQLite المعتمدة إذا كانت مطلوبة لإعادة إنتاج التحليل التاريخي كاملًا."),
        "- اعتماد عملة موحدة (USD أو EGP أو SAR) ومصدر/تاريخ صرف موثق قبل تحويل القيم.",
        "- اعتماد افتراضات واضحة لتحويل الساعة/اليوم/الأسبوع/الشهر إلى سنة قبل إنتاج راتب سنوي مقارن.",
        "- مراجعة تقديرات الرواتب القديمة وربط كل تقدير بمصدر وتاريخ ومطابقة مناسبة للدولة والمسمى ومستوى الخبرة؛ حتى ذلك الوقت تُعرض كغير متحققة وتُستبعد.",
        "- عدم تقديم الرواتب على أنها إعلانات نشطة أو قيم مؤكدة دون فحص المصدر الأصلي.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def _notebook_cell(cell_type: str, source: str, execution_count: int | None = None, outputs: list[Any] | None = None) -> dict[str, Any]:
    cell: dict[str, Any] = {
        "cell_type": cell_type,
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }
    if cell_type == "code":
        cell["execution_count"] = execution_count
        cell["outputs"] = outputs or []
    return cell


def write_cleaning_notebook(path: Path, summary: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    missing = summary.get("missing_required_sources", [])
    missing_text = ", ".join(f"`{name}`" for name in missing) if missing else "لا توجد ملفات مصدر إلزامية مفقودة"
    missing_note = (
        "هذه نتيجة جزئية ولا تشمل كل مصادر الأرشيف المحددة."
        if missing
        else "كل مصادر الوظائف المعلنة متاحة لهذا التشغيل؛ لا يتضمن ذلك قاعدة SQLite أو حزمة Parquet المعتمدة غير الموجودة في مساحة العمل."
    )
    markdown = f"""# دفتر تدقيق وتنظيف بيانات الوظائف التقنية

**تاريخ التنفيذ:** {summary.get('audit_date', '')}<br>
**مرجع البيانات:** `{summary.get('source_ref', '')}`<br>
**الملف المنظف:** `{summary.get('cleaned_dataset_path', '')}`

## النطاق

شُغّل الـpipeline على {summary.get('available_job_source_count', 0)} مصادر متاحة، بإجمالي {summary.get('output_rows', 0):,} صفًا. الملفات الخام للقراءة فقط، ويحتفظ `source_row_json` بصف المصدر الأصلي كاملًا. لم تُحذف التكرارات أو القيم الشاذة.

**مصادر مفقودة:** {missing_text}. {missing_note}

## سياسة التنظيف

- تطبيع المسافات والأسماء ذات المرادف الصريح فقط؛ لا دمج تخميني لعناوين الوظائف أو الدول.
- تحليل تواريخ النشر من أعمدة النشر فقط. حقل `updated` لا يُعامل كتاريخ نشر.
- الحفاظ على نص الراتب وقيم المصدر والعملة والفترة ومراجعها. التقديرات الموروثة موسومة وغير متحققة ومستبعدة من إحصاءات الرواتب الفعلية.
- لا تقدير جديد ولا ملء للراتب المفقود. لا تحويل FX أو سنونة للفترات غير السنوية قبل اعتماد سياسة العملة وسعر الصرف وعوامل السنونة.
- الإحصاءات الفعلية مجمعة حسب المسمى والدولة/النطاق والعملة والفترة؛ متوسط/وسيط القيمة يمثل منتصف النطاق المعلن.

## نتائج التنفيذ

- الصفوف قبل/بعد: **{summary.get('input_rows', 0):,} / {summary.get('output_rows', 0):,}**؛ المحذوف **0**.
- تكرارات دقيقة محفوظة ومعلّمة: **{summary.get('exact_duplicate_occurrences_retained', 0):,}**.
- رواتب `actual_reported`: **{summary.get('salary', {}).get('actual_reported_records', 0):,}**؛ منها المؤهل لإحصاءات حسب العملة والفترة: **{summary.get('salary', {}).get('actual_statistics_eligible_records', 0):,}**.
- تقديرات موروثة غير متحققة: **{summary.get('salary', {}).get('legacy_estimate_unverified_records', 0):,}**؛ لا تُخلط مع الفعلي.
- الرواتب المفقودة التي بقيت مفقودة: **{summary.get('salary', {}).get('missing_records', 0):,}**.
- قاعدة بيانات المشروع: **{summary.get('existing_database_status', 'غير متاحة')}**؛ اختبار SQLite بالذاكرة: **{summary.get('sqlite_round_trip', {}).get('status', 'غير متاح')}**.

## التشغيل من جديد

بعد توفير جميع ملفات المصدر في مجلد واحد، شغّل:

```bash
python scripts/data_cleaning/build_cleaning_audit.py \\
  --raw-data-directory data/raw \\
  --source-ref "main@<commit>"
```

استخدم ملف سياسة صريحًا فقط بعد اعتماده، عبر `--salary-policy-file`; من دون ذلك تبقى تحويلات العملة والسنونة غير مطبقة.
"""
    code_root = """from pathlib import Path
import csv
import gzip
import json


def find_project_root(start=None):
    current = Path(start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "scripts" / "data_cleaning" / "build_cleaning_audit.py").is_file():
            return candidate
    raise FileNotFoundError("Could not locate the repository root from the notebook working directory")


PROJECT_ROOT = find_project_root()
REPORT_DIR = PROJECT_ROOT / "analysis" / "reports" / "data_cleaning"
DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "jobs_cleaned_audited.csv.gz"
SUMMARY = json.loads((REPORT_DIR / "cleaning_summary.json").read_text(encoding="utf-8"))
BEFORE = json.loads((REPORT_DIR / "data_quality_before.json").read_text(encoding="utf-8"))
AFTER = json.loads((REPORT_DIR / "data_quality_after.json").read_text(encoding="utf-8"))


def read_csv_rows(path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


print("scope:", SUMMARY["scope"])
print("rows before / after:", SUMMARY["input_rows"], SUMMARY["output_rows"])
print("dataset:", DATASET_PATH)
"""
    code_sources = """manifest = read_csv_rows(REPORT_DIR / "source_manifest.csv")
print("Source manifest (including missing files and base-export references)")
for item in manifest:
    print(item["status"], item["role"], item["file"], item["sha256"][:12])

print("\\nBase/enriched skill comparisons")
for filename, result in SUMMARY["base_enriched_pair_audit"].items():
    print(filename, result["status"], result["matched_ids_with_changed_skills"], "changed IDs")
"""
    code_example = """with gzip.open(DATASET_PATH, "rt", encoding="utf-8", newline="") as handle:
    example = next(csv.DictReader(handle))
source_row = json.loads(example["source_row_json"])
print("Raw source values retained:", {
    "title": source_row.get("title", source_row.get("job_title", "")),
    "country": source_row.get("country", source_row.get("job_country", "")),
    "salary": source_row.get("salary", source_row.get("salary_raw", "")),
})
print("Derived fields:", {
    "title_clean": example["title_clean"],
    "country_standardized": example["country_standardized"],
    "posted_at_iso": example["posted_at_iso"],
    "source_updated_at_iso": example["source_updated_at_iso"],
    "skills_tokens_json": example["skills_tokens_json"],
    "salary_currency_code": example["salary_currency_code"],
    "salary_period_code": example["salary_period_code"],
    "salary_value_type": example["salary_value_type"],
})
"""
    code_quality = """print("Before-cleaning field coverage")
for field, values in BEFORE["field_coverage"].items():
    print(f"{field:30} present={values['present']:>8} missing={values['missing']:>8}")

print("\\nAfter-cleaning field coverage")
for field, values in AFTER["field_coverage"].items():
    print(f"{field:30} present={values['present']:>8} missing={values['missing']:>8}")

print("\\nCleaning invariants")
print("rows dropped:", SUMMARY["rows_dropped"])
print("exact duplicate occurrences retained:", SUMMARY["exact_duplicate_occurrences_retained"])
print("raw source files unchanged:", SUMMARY["source_integrity"]["all_unchanged_during_run"])
"""
    code_salary = """from itertools import islice

salary_stats_path = REPORT_DIR / "salary_statistics_actual.csv"
with gzip.open(DATASET_PATH, "rt", encoding="utf-8", newline="") as handle:
    cleaned_reader = csv.DictReader(handle)
    cleaned_sample = list(islice(cleaned_reader, 5))
    cleaned_row_count = len(cleaned_sample) + sum(1 for _ in cleaned_reader)

print("cleaned rows:", cleaned_row_count)
print("salary value-type counts:", SUMMARY["salary"]["value_type_counts"])
print("actual-statistics-eligible rows:", SUMMARY["salary"]["actual_statistics_eligible_records"])
print("currency policy:", SUMMARY["salary_policy"]["status"])
print("FX conversion applied:", SUMMARY["salary_policy"].get("fx_conversion_applied", False))
print("non-year annualization policy:", SUMMARY["salary_policy"].get("annualization_factors", {}))

salary_stats = read_csv_rows(salary_stats_path)
print("actual salary groups:", len(salary_stats))
for row in salary_stats[:10]:
    print({key: row[key] for key in (
        "country", "title_display", "salary_currency_code", "salary_period_code",
        "actual_record_count", "average_of_record_midpoints_native", "median_of_record_midpoints_native"
    )})
"""
    code_validation = """# Every source row is retained; duplicate and outlier flags are review metadata, not deletion rules.
assert SUMMARY["input_rows"] == SUMMARY["output_rows"]
assert SUMMARY["rows_dropped"] == 0
assert cleaned_row_count == SUMMARY["output_rows"]
assert SUMMARY["sqlite_round_trip"]["status"] == "passed"

# The old project database is checked separately from this in-memory round-trip.
print("existing database:", SUMMARY["existing_database_status"])
print("in-memory SQLite salary-group check:", SUMMARY["sqlite_round_trip"])
"""
    notebook = {
        "cells": [
            _notebook_cell("markdown", markdown),
            _notebook_cell("markdown", "## 1. تحميل النتائج وجرد المدخلات\n\nالخلايا التالية تستخدم Python القياسي فقط. يبدأ التدقيق بمرجع النسخة وmanifest والبصمات؛ الملفات الخام تُقرأ ولا تُعدّل."),
            _notebook_cell("code", code_root),
            _notebook_cell("code", code_sources),
            _notebook_cell("markdown", "## 2. مثال على صف خام ومشتقاته\n\nيعرض هذا المثال حقولًا محددة فقط، ويقارن القيمة الأصلية بالعمود المشتق. `source_row_json` يحفظ كامل صف المصدر، أما `title_key` فيطابق النص بعد casefold/مسافات فقط ولا يدمج الأدوار دلاليًا."),
            _notebook_cell("code", code_example),
            _notebook_cell("markdown", "## 3. جودة البيانات قبل التنظيف وبعده\n\nالمفقود يبقى مفقودًا؛ تُعرض أيضًا التواريخ القديمة/المستقبلية، النصوص المشكوك بترميزها، والتكرارات كإشارات مراجعة فقط."),
            _notebook_cell("code", code_quality),
            _notebook_cell("markdown", "## 4. الرواتب والتحليل المعاد تشغيله\n\nلا تستخدم متوسطًا موحدًا بين عملات أو فترات مختلفة. الإحصاءات تقتصر على مبالغ `actual_reported` ذات العملة والفترة الصريحتين، بعد حجب القيم التي تحتاج مراجعة واسعة. التقديرات القديمة غير المتحققة منفصلة، ولا تُستخدم لتعبئة المفقود."),
            _notebook_cell("code", code_salary),
            _notebook_cell("markdown", "## 5. اختبارات الاحتفاظ والاتساق\n\nالتكرار أو الشذوذ يوسم للمراجعة ولا يؤدي للحذف. اختبار SQLite داخل الذاكرة يراجع اتساق CSV والإحصاءات فقط؛ لا يحل محل المقارنة بقاعدة المشروع غير الموجودة."),
            _notebook_cell("code", code_validation),
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_pipeline(
    raw_directory: Path,
    dataset_path: Path,
    report_directory: Path,
    *,
    source_ref: str = "unspecified",
    as_of_date: dt.date | None = None,
    salary_policy_file: Path | None = None,
    require_all_sources: bool = False,
    notebook_path: Path | None = None,
) -> dict[str, Any]:
    raw_directory = raw_directory.resolve()
    dataset_path = dataset_path.resolve()
    report_directory = report_directory.resolve()
    audit_date = as_of_date or dt.datetime.now(dt.timezone.utc).date()
    salary_policy = _load_salary_policy(salary_policy_file.resolve() if salary_policy_file else None)
    report_directory.mkdir(parents=True, exist_ok=True)
    dataset_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = _source_manifest(raw_directory)
    missing_required = [item["file"] for item in manifest if item["status"] == "missing_required_source"]
    if require_all_sources and missing_required:
        raise FileNotFoundError("Missing required source files:\n- " + "\n- ".join(missing_required))

    before_counts: Counter[str] = Counter()
    after_counts: Counter[str] = Counter()
    before_by_file: dict[str, Counter[str]] = defaultdict(Counter)
    file_reports: dict[str, Any] = {}
    country_counts: dict[str, Counter[str]] = defaultdict(Counter)
    role_country_counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    skill_counts: dict[str, Counter[str]] = defaultdict(Counter)
    estimate_sources: dict[tuple[str, str, str, str, str, str], Counter[str]] = defaultdict(Counter)
    salary_review_candidates: list[dict[str, str]] = []
    salary_group_points: dict[tuple[str, str, str, str], list[tuple[float, float, float, str]]] = defaultdict(list)
    salary_group_files: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    display_titles: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    salary_value_types: Counter[str] = Counter()
    salary_parse_statuses: Counter[str] = Counter()
    currency_statuses: Counter[str] = Counter()
    period_statuses: Counter[str] = Counter()
    date_flags: Counter[str] = Counter()
    numeric_salary_records = 0
    numeric_currency_missing_or_conflict_records = 0
    numeric_period_unknown_records = 0
    exact_duplicate_total = 0
    output_rows = 0
    input_rows = 0
    possible_mojibake_records = 0
    date_out_of_range_records = 0
    raw_before_hashes = {item["file"]: item["sha256"] for item in manifest if item["exists"]}
    skill_aliases = _load_skill_reference()
    base_skill_data: dict[str, tuple[dict[str, str] | None, set[str], bool]] = {}
    for enriched_name, base_name in BASE_EXPORTS.items():
        base_path = raw_directory / base_name
        if base_path.is_file():
            base_map, duplicate_ids = _load_base_skill_map(base_path)
            base_skill_data[enriched_name] = (base_map, duplicate_ids, True)
        else:
            base_skill_data[enriched_name] = (None, set(), False)
    source_id_duplicate_occurrences = 0
    source_files_used = 0
    per_file_after_counts: dict[str, Counter[str]] = defaultdict(Counter)

    with tempfile.TemporaryDirectory(prefix="jop-cleaning-audit-") as temp_directory_name:
        temp_path = Path(temp_directory_name) / "cleaning_intermediate.csv.gz"
        temp_handle, temp_writer = _csv_writer(temp_path, INTERMEDIATE_FIELDS)
        try:
            for spec in JOB_SOURCE_SPECS:
                source_path = raw_directory / spec["file"]
                if not source_path.is_file():
                    file_reports[spec["file"]] = {
                        "source_dataset": spec["dataset"],
                        "status": "missing_required_source",
                        "rows": 0,
                        "exact_duplicate_occurrences_retained": 0,
                        "missing_fields_before": {},
                        "missing_fields_after": {},
                    }
                    continue

                source_files_used += 1
                file_report: dict[str, Any] = {
                    "source_dataset": spec["dataset"],
                    "status": "processed",
                    "source_sha256": raw_before_hashes.get(spec["file"], ""),
                    "rows": 0,
                    "exact_duplicate_occurrences_retained": 0,
                    "duplicate_source_id_occurrences_retained": 0,
                    "missing_fields_before": {},
                    "missing_fields_after": {},
                    "salary_value_type_counts": Counter(),
                    "salary_parse_status_counts": Counter(),
                    "currency_detection_status_counts": Counter(),
                    "period_detection_status_counts": Counter(),
                    "skills_enrichment_status_counts": Counter(),
                    "skill_duplicate_tokens_removed": 0,
                    "possible_mojibake_records": 0,
                    "date_out_of_expected_range_records": 0,
                }
                exact_digests: set[str] = set()
                seen_source_ids: set[str] = set()
                # Large descriptions stay on disk in the compressed intermediate file.
                with _open_source_rows(source_path, spec["kind"]) as rows:
                    for row_number, row in enumerate(rows, start=1):
                        input_rows += 1
                        file_report["rows"] += 1
                        identifier = source_value(row, "id", "job_id", "row_id")
                        duplicate_id_occurrence = bool(identifier and identifier in seen_source_ids)
                        if identifier:
                            seen_source_ids.add(identifier)
                            if duplicate_id_occurrence:
                                source_id_duplicate_occurrences += 1
                                file_report["duplicate_source_id_occurrences_retained"] += 1

                        digest = _source_row_digest(row)
                        exact_duplicate = digest in exact_digests
                        exact_digests.add(digest)
                        if exact_duplicate:
                            exact_duplicate_total += 1
                            file_report["exact_duplicate_occurrences_retained"] += 1

                        for metric in PRE_QUALITY_FIELDS:
                            present = _metric_value(row, metric)
                            if present:
                                before_counts[metric] += 1
                                before_by_file[spec["file"]][metric] += 1

                        base_skill_map, base_duplicate_ids, base_available = base_skill_data.get(
                            spec["file"], (None, set(), False)
                        )
                        record = build_clean_record(
                            row,
                            spec["file"],
                            spec["dataset"],
                            spec["bucket"],
                            row_number,
                            skill_aliases,
                            salary_policy,
                            audit_date,
                            exact_duplicate=exact_duplicate,
                            duplicate_source_id_occurrence=duplicate_id_occurrence,
                            base_skill_map=base_skill_map,
                            base_skill_duplicate_ids=base_duplicate_ids,
                            base_source_available=base_available,
                        )
                        temp_writer.writerow(record)
                        output_rows += 1

                        file_report["salary_value_type_counts"][record["salary_value_type"]] += 1
                        file_report["salary_parse_status_counts"][record["salary_parse_status"]] += 1
                        file_report["currency_detection_status_counts"][record["salary_currency_detection_status"]] += 1
                        file_report["period_detection_status_counts"][record["salary_period_detection_status"]] += 1
                        file_report["skills_enrichment_status_counts"][record["skills_enrichment_status"]] += 1
                        file_report["skill_duplicate_tokens_removed"] += int(record["skill_duplicate_token_count"] or 0)
                        if record["encoding_suspected_mojibake"] == "yes":
                            file_report["possible_mojibake_records"] += 1
                            possible_mojibake_records += 1
                        salary_value_types[record["salary_value_type"]] += 1
                        salary_parse_statuses[record["salary_parse_status"]] += 1
                        currency_statuses[record["salary_currency_detection_status"]] += 1
                        period_statuses[record["salary_period_detection_status"]] += 1
                        if record["salary_parse_status"] in {"parsed_single_amount", "parsed_range", "range_order_reversed"}:
                            numeric_salary_records += 1
                            if (
                                not record["salary_currency_code"]
                                or record["salary_currency_detection_status"] in {
                                    "ambiguous_currency_symbol",
                                    "conflict_between_source_column_and_salary_text",
                                    "conflicting_currency_codes_in_text",
                                    "unrecognized_source_currency_value",
                                }
                            ):
                                numeric_currency_missing_or_conflict_records += 1
                            if record["salary_period_code"] == "UNKNOWN":
                                numeric_period_unknown_records += 1
                        date_quality_values = [
                            value for value in (record["date_quality_flags"] or "").split(";") if value
                        ]
                        for date_flag in date_quality_values:
                            date_flags[date_flag] += 1
                        if any("date_before_2000" in flag or "date_after_audit_date" in flag for flag in date_quality_values):
                            file_report["date_out_of_expected_range_records"] += 1
                        if date_quality_values and any("date_before_2000" in flag or "date_after_audit_date" in flag for flag in date_quality_values):
                            date_out_of_range_records += 1

                        country = record["country_standardized"] or "__MISSING_COUNTRY__"
                        title_key = record["title_key"] or "__MISSING_TITLE__"
                        display_title = record["title_clean"] or "__MISSING_TITLE__"
                        country_counts[country]["job_records"] += 1
                        country_counts[country]["distinct_title_keys"] += 0
                        display_titles[(country, title_key)][display_title] += 1
                        role_counts = role_country_counts[(country, title_key)]
                        role_counts["total_job_records"] += 1
                        role_counts["actual_reported_records"] += int(record["salary_value_type"] == "actual_reported")
                        role_counts["actual_statistics_eligible_records"] += int(record["salary_statistics_eligible"] == "yes")
                        role_counts["estimated_legacy_unverified_records"] += int(record["salary_value_type"] == "estimated_legacy_unverified")
                        role_counts["source_reported_unverified_records"] += int(record["salary_value_type"] == "source_reported_unverified")
                        role_counts["not_disclosed_records"] += int(record["salary_value_type"] == "not_disclosed")
                        role_counts["missing_salary_records"] += int(record["salary_value_type"] == "missing")
                        role_counts["unparseable_salary_records"] += int(record["salary_value_type"] == "unparseable_or_no_numeric_amount")
                        role_counts["records_without_currency_or_period"] += int(
                            record["salary_value_type"] == "actual_reported" and record["salary_statistics_eligible"] != "yes"
                        )
                        country_counts[country]["actual_reported_salary_records"] += int(record["salary_value_type"] == "actual_reported")
                        country_counts[country]["actual_statistics_eligible_records"] += int(record["salary_statistics_eligible"] == "yes")
                        country_counts[country]["estimated_legacy_unverified_records"] += int(record["salary_value_type"] == "estimated_legacy_unverified")
                        country_counts[country]["missing_salary_records"] += int(record["salary_value_type"] in {"missing", "not_disclosed"})

                        if record["salary_value_type"] == "estimated_legacy_unverified":
                            estimate_key = (
                                spec["dataset"],
                                record["salary_source_raw"],
                                record["salary_sources_raw"],
                                record["salary_fill_source_raw"],
                                record["salary_basis_raw"],
                                record["salary_currency_raw"],
                            )
                            estimate_sources[estimate_key]["rows"] += 1

                        if record["salary_value_type"] in {
                            "actual_reported", "source_reported_unverified", "unparseable_or_no_numeric_amount"
                        } and (
                            record["salary_statistics_eligible"] != "yes"
                            or record["salary_value_type"] == "unparseable_or_no_numeric_amount"
                            or bool(record["salary_integrity_flags"])
                        ):
                            review_reasons = [record["salary_comparability_status"]]
                            if record["salary_parse_status"] not in {"parsed_single_amount", "parsed_range"}:
                                review_reasons.append(record["salary_parse_status"])
                            if record["salary_integrity_flags"]:
                                review_reasons.extend(record["salary_integrity_flags"].split(";"))
                            salary_review_candidates.append({
                                "record_id": record["record_id"],
                                "source_dataset": record["source_dataset"],
                                "source_file": record["source_file"],
                                "source_row_number": record["source_row_number"],
                                "source_record_id": record["source_record_id"],
                                "title": record["title_clean"],
                                "country": record["country_standardized"],
                                "salary_value_type": record["salary_value_type"],
                                "salary_raw": record["salary_raw"],
                                "salary_candidate_raw": record["salary_candidate_raw"],
                                "salary_min_original_currency": record["salary_min_original_currency"],
                                "salary_max_original_currency": record["salary_max_original_currency"],
                                "salary_currency_code": record["salary_currency_code"],
                                "salary_currency_detection_status": record["salary_currency_detection_status"],
                                "salary_period_code": record["salary_period_code"],
                                "salary_period_detection_status": record["salary_period_detection_status"],
                                "salary_source_raw": record["salary_source_raw"],
                                "salary_sources_raw": record["salary_sources_raw"],
                                "source_url": record["source_url_raw"],
                                "review_reason": ";".join(dict.fromkeys(filter(None, review_reasons))),
                            })

                        raw_skill_tokens = source_reader.split_skill_labels(record["skills_raw"], spec["file"], deduplicate=False)
                        for token in raw_skill_tokens:
                            metadata = source_reader.resolve_skill_metadata(token, skill_aliases)
                            skill_id = metadata["skill_id"]
                            aggregate = skill_counts[skill_id]
                            aggregate["skill_label"] = token
                            aggregate["skill_category"] = metadata["category"]
                            aggregate["skill_match_policy"] = metadata["match_policy"]
                            aggregate["skill_review_status"] = metadata["review_status"]
                            aggregate["raw_token_occurrences"] += 1
                            aggregate[f"source:{spec['dataset']}"] += 1
                        for skill_id in set(json.loads(record["skill_ids_json"])):
                            skill_counts[skill_id]["job_record_count"] += 1

                        if record["salary_statistics_eligible"] == "yes":
                            group_key = _salary_group_key(record)
                            midpoint = float(record["salary_midpoint_original_currency"])
                            lower = float(record["salary_min_original_currency"])
                            upper = float(record["salary_max_original_currency"])
                            salary_group_points[group_key].append((midpoint, lower, upper, record["record_id"]))
                            salary_group_files[group_key].add(spec["file"])

                        for metric, column in (
                            ("title_clean", "title_clean"),
                            ("company_clean", "company_clean"),
                            ("country_standardized", "country_standardized"),
                            ("description_raw", "description_raw"),
                            ("source_url_raw", "source_url_raw"),
                            ("skills_raw", "skills_raw"),
                        ):
                            if source_reader.contains_source_value(record[column]):
                                after_counts[metric] += 1
                                per_file_after_counts[spec["file"]][metric] += 1
                        if record["salary_parse_status"] in {"parsed_single_amount", "parsed_range", "range_order_reversed"}:
                            after_counts["salary_numeric_parsed"] += 1
                        if record["posted_at_iso"]:
                            after_counts["posted_date_parsed"] += 1
                        if record["source_updated_at_iso"]:
                            after_counts["source_updated_at_parsed"] += 1
                        if record["skills_tokens_json"] != "[]":
                            after_counts["skills_tokens_parsed"] += 1
                        if record["source_url_syntax_status"] == "syntactically_valid_http_url":
                            after_counts["source_url_syntax_valid"] += 1
                            per_file_after_counts[spec["file"]]["source_url_syntax_valid"] += 1
                        if record["posted_at_iso"]:
                            per_file_after_counts[spec["file"]]["posted_date_parsed"] += 1
                        if record["source_updated_at_iso"]:
                            per_file_after_counts[spec["file"]]["source_updated_at_parsed"] += 1
                        if record["skills_tokens_json"] != "[]":
                            per_file_after_counts[spec["file"]]["skills_tokens_parsed"] += 1
                        if record["salary_parse_status"] in {"parsed_single_amount", "parsed_range", "range_order_reversed"}:
                            per_file_after_counts[spec["file"]]["salary_numeric_parsed"] += 1
                file_report["missing_fields_before"] = {
                    field: file_report["rows"] - before_by_file[spec["file"]].get(field, 0)
                    for field in PRE_QUALITY_FIELDS
                }
                file_report["missing_fields_after"] = {
                    "title_clean": file_report["rows"] - per_file_after_counts[spec["file"]].get("title_clean", 0),
                    "company_clean": file_report["rows"] - per_file_after_counts[spec["file"]].get("company_clean", 0),
                    "country_standardized": file_report["rows"] - per_file_after_counts[spec["file"]].get("country_standardized", 0),
                    "description_raw": file_report["rows"] - per_file_after_counts[spec["file"]].get("description_raw", 0),
                    "source_url_syntax_valid": file_report["rows"] - per_file_after_counts[spec["file"]].get("source_url_syntax_valid", 0),
                    "skills_tokens_parsed": file_report["rows"] - per_file_after_counts[spec["file"]].get("skills_tokens_parsed", 0),
                    "posted_date_parsed": file_report["rows"] - per_file_after_counts[spec["file"]].get("posted_date_parsed", 0),
                    "source_updated_at_parsed": file_report["rows"] - per_file_after_counts[spec["file"]].get("source_updated_at_parsed", 0),
                    "salary_numeric_parsed": file_report["rows"] - per_file_after_counts[spec["file"]].get("salary_numeric_parsed", 0),
                }
                file_report["salary_value_type_counts"] = dict(file_report["salary_value_type_counts"])
                file_report["salary_parse_status_counts"] = dict(file_report["salary_parse_status_counts"])
                file_report["currency_detection_status_counts"] = dict(file_report["currency_detection_status_counts"])
                file_report["period_detection_status_counts"] = dict(file_report["period_detection_status_counts"])
                file_report["skills_enrichment_status_counts"] = dict(file_report["skills_enrichment_status_counts"])
                file_reports[spec["file"]] = file_report
        finally:
            temp_handle.close()

        for country in country_counts:
            country_counts[country]["distinct_title_keys"] = sum(
                1 for current_country, _ in display_titles if current_country == country
            )

        outlier_thresholds: dict[tuple[str, str, str, str], tuple[float, float]] = {}
        outlier_record_ids: set[str] = set()
        outlier_counts: Counter[tuple[str, str, str, str]] = Counter()
        for group_key, points in salary_group_points.items():
            values = [point[0] for point in points]
            if len(values) < 8:
                continue
            q1, q3 = _quantile(values, 0.25), _quantile(values, 0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            outlier_thresholds[group_key] = (lower_bound, upper_bound)
            for midpoint, _, _, record_id in points:
                if midpoint < lower_bound or midpoint > upper_bound:
                    outlier_record_ids.add(record_id)
                    outlier_counts[group_key] += 1

        actual_stats = _stats_rows(salary_group_points, outlier_counts, display_titles, salary_group_files)
        stats_path = report_directory / "salary_statistics_actual.csv"
        stat_fields = [
            "country", "title_display", "title_key", "salary_currency_code", "salary_period_code",
            "actual_record_count", "estimated_record_count", "average_of_record_midpoints_native",
            "median_of_record_midpoints_native", "minimum_reported_lower_bound_native",
            "maximum_reported_upper_bound_native", "minimum_record_midpoint_native",
            "maximum_record_midpoint_native", "potential_iqr_outlier_records_included", "source_files",
            "statistics_scope", "fx_conversion_applied",
        ]
        _write_plain_csv(stats_path, stat_fields, actual_stats)

        final_handle, final_writer = _csv_writer(dataset_path, OUTPUT_FIELDS)
        final_rows = 0
        final_ids: set[str] = set()
        salary_review_ids = {item["record_id"] for item in salary_review_candidates}
        try:
            with gzip.open(temp_path, "rt", encoding="utf-8", newline="") as source_handle:
                reader = csv.DictReader(source_handle)
                for record in reader:
                    final_rows += 1
                    if record["record_id"] in final_ids:
                        raise AssertionError(f"Duplicate staging record_id: {record['record_id']}")
                    final_ids.add(record["record_id"])
                    eligible = record["salary_statistics_eligible"] == "yes"
                    group_key = _salary_group_key(record)
                    if not eligible:
                        record["salary_iqr_outlier_flag"] = "not_eligible_for_grouped_salary_outlier_check"
                    elif record["record_id"] in outlier_record_ids:
                        record["salary_iqr_outlier_flag"] = "potential_iqr_outlier_review_only"
                        record["salary_integrity_flags"] = ";".join(filter(None, [record["salary_integrity_flags"], "potential_iqr_outlier_review_only"]))
                        record["data_quality_flags"] = ";".join(filter(None, [record["data_quality_flags"], "potential_iqr_outlier_review_only_not_deleted"]))
                        if record["record_id"] not in salary_review_ids:
                            salary_review_candidates.append({
                                "record_id": record["record_id"],
                                "source_dataset": record["source_dataset"],
                                "source_file": record["source_file"],
                                "source_row_number": record["source_row_number"],
                                "source_record_id": record["source_record_id"],
                                "title": record["title_clean"],
                                "country": record["country_standardized"],
                                "salary_value_type": record["salary_value_type"],
                                "salary_raw": record["salary_raw"],
                                "salary_candidate_raw": record["salary_candidate_raw"],
                                "salary_min_original_currency": record["salary_min_original_currency"],
                                "salary_max_original_currency": record["salary_max_original_currency"],
                                "salary_currency_code": record["salary_currency_code"],
                                "salary_currency_detection_status": record["salary_currency_detection_status"],
                                "salary_period_code": record["salary_period_code"],
                                "salary_period_detection_status": record["salary_period_detection_status"],
                                "salary_source_raw": record["salary_source_raw"],
                                "salary_sources_raw": record["salary_sources_raw"],
                                "source_url": record["source_url_raw"],
                                "review_reason": "potential_iqr_outlier_review_only",
                            })
                    elif group_key in outlier_thresholds:
                        record["salary_iqr_outlier_flag"] = "not_iqr_outlier"
                    else:
                        record["salary_iqr_outlier_flag"] = "group_below_minimum_8_records"
                    final_writer.writerow(record)
        finally:
            final_handle.close()

    if final_rows != input_rows or output_rows != input_rows:
        raise AssertionError(f"Row-retention invariant failed: input={input_rows}, output={output_rows}, final={final_rows}")

    after_report = {
        "metadata": {
            "audit_date": audit_date.isoformat(),
            "source_ref": source_ref,
            "scope": "available sources only; missing files are listed and no rows are synthesized",
            "cleaned_dataset_path": _workspace_path_label(dataset_path),
        },
        "rows": {"before": input_rows, "after": final_rows, "dropped": input_rows - final_rows},
        "field_coverage": {
            "title_clean": {"present": after_counts["title_clean"], "missing": final_rows - after_counts["title_clean"]},
            "company_clean": {"present": after_counts["company_clean"], "missing": final_rows - after_counts["company_clean"]},
            "country_standardized": {"present": after_counts["country_standardized"], "missing": final_rows - after_counts["country_standardized"]},
            "description_raw": {"present": after_counts["description_raw"], "missing": final_rows - after_counts["description_raw"]},
            "source_url_raw": {"present": after_counts["source_url_raw"], "missing": final_rows - after_counts["source_url_raw"]},
            "skills_raw": {"present": after_counts["skills_raw"], "missing": final_rows - after_counts["skills_raw"]},
            "salary_numeric_parsed": {"present": after_counts["salary_numeric_parsed"], "missing": final_rows - after_counts["salary_numeric_parsed"]},
            "posted_date_parsed": {"present": after_counts["posted_date_parsed"], "missing": final_rows - after_counts["posted_date_parsed"]},
            "source_updated_at_parsed": {"present": after_counts["source_updated_at_parsed"], "missing": final_rows - after_counts["source_updated_at_parsed"]},
            "skills_tokens_parsed": {"present": after_counts["skills_tokens_parsed"], "missing": final_rows - after_counts["skills_tokens_parsed"]},
            "source_url_syntax_valid": {"present": after_counts["source_url_syntax_valid"], "missing": final_rows - after_counts["source_url_syntax_valid"]},
        },
        "salary": {
            "value_type_counts": dict(salary_value_types),
            "parse_status_counts": dict(salary_parse_statuses),
            "currency_detection_status_counts": dict(currency_statuses),
            "period_detection_status_counts": dict(period_statuses),
            "numeric_parseable_records": numeric_salary_records,
            "actual_reported_records": salary_value_types.get("actual_reported", 0),
            "actual_statistics_eligible_records": sum(len(values) for values in salary_group_points.values()),
            "legacy_estimate_unverified_records": salary_value_types.get("estimated_legacy_unverified", 0),
            "source_reported_unverified_records": salary_value_types.get("source_reported_unverified", 0),
            "not_disclosed_records": salary_value_types.get("not_disclosed", 0),
            "missing_records": salary_value_types.get("missing", 0),
            "unparseable_records": salary_value_types.get("unparseable_or_no_numeric_amount", 0),
            "currency_missing_or_conflict_records": numeric_currency_missing_or_conflict_records,
            "period_unknown_records": numeric_period_unknown_records,
            "potential_iqr_outlier_records_review_only": len(outlier_record_ids),
            "absolute_scale_review_records": sum(
                1 for item in salary_review_candidates
                if "salary_below_broad_period_screening_floor_review_only" in item["review_reason"]
                or "salary_above_broad_period_screening_ceiling_review_only" in item["review_reason"]
            ),
            "statistics_group_count": len(actual_stats),
            "estimates_added_by_this_run": 0,
            "review_candidate_records": len(salary_review_candidates),
        },
        "date_quality_flag_counts": dict(date_flags),
        "date_out_of_expected_range_records": date_out_of_range_records,
        "possible_mojibake_records": possible_mojibake_records,
        "exact_duplicate_occurrences_retained": exact_duplicate_total,
        "duplicate_source_id_occurrences_retained": source_id_duplicate_occurrences,
        "country_or_scope_counts": {key: value["job_records"] for key, value in sorted(country_counts.items())},
        "unique_title_country_pairs": len(role_country_counts),
        "source_files": file_reports,
        "base_enriched_pair_audit": _audit_base_pairs(raw_directory),
    }
    before_report = {
        "metadata": {
            "audit_date": audit_date.isoformat(),
            "source_ref": source_ref,
            "definition": "coverage measured on source values before any derived normalization; non-disclosure text is not a numeric salary",
        },
        "rows": input_rows,
        "field_coverage": _coverage_dict(input_rows, before_counts),
        "source_file_rows": {name: report.get("rows", 0) for name, report in file_reports.items()},
        "exact_duplicate_occurrences_retained": exact_duplicate_total,
        "duplicate_source_id_occurrences_retained": source_id_duplicate_occurrences,
    }

    # Raw inputs are checksummed again after processing; this run must be read-only.
    after_manifest = _source_manifest(raw_directory)
    after_hashes = {item["file"]: item["sha256"] for item in after_manifest if item["exists"]}
    unchanged_files = [name for name, digest in raw_before_hashes.items() if after_hashes.get(name) == digest]
    changed_files = [name for name, digest in raw_before_hashes.items() if after_hashes.get(name) != digest]
    source_integrity = {
        "all_unchanged_during_run": not changed_files,
        "files_hashed_before": len(raw_before_hashes),
        "files_hashed_unchanged": len(unchanged_files),
        "changed_or_disappeared_files": changed_files,
    }
    if changed_files:
        raise RuntimeError("Raw inputs changed while the cleaning run was in progress: " + ", ".join(changed_files))

    profile_paths = _write_profile_outputs(
        report_directory,
        role_country_counts,
        country_counts,
        skill_counts,
        estimate_sources,
        salary_policy,
    )
    salary_review_path = report_directory / "salary_review_candidates.csv"
    _write_plain_csv(
        salary_review_path,
        [
            "record_id", "source_dataset", "source_file", "source_row_number", "source_record_id", "title", "country",
            "salary_value_type", "salary_raw", "salary_candidate_raw", "salary_min_original_currency",
            "salary_max_original_currency", "salary_currency_code", "salary_currency_detection_status",
            "salary_period_code", "salary_period_detection_status", "salary_source_raw", "salary_sources_raw",
            "source_url", "review_reason",
        ],
        salary_review_candidates,
    )
    sqlite_check = _sqlite_round_trip_check(dataset_path, actual_stats)
    if sqlite_check["status"] != "passed":
        raise AssertionError("SQLite round-trip aggregate validation failed: " + "; ".join(sqlite_check["mismatches"]))

    local_database_path = PROJECT_ROOT / "data" / "processed" / "job_market.sqlite3"
    full_archive_path = PROJECT_ROOT / "data" / "processed" / "full_archive_parquet_v1_20261028"
    existing_database_status = "available_not_compared" if local_database_path.is_file() else "not_available_in_current_checkout"
    archive_status = "available" if full_archive_path.exists() else "not_available_in_current_checkout"

    dataset_hash = sha256_file(dataset_path)
    report_before_path = report_directory / "data_quality_before.json"
    report_after_path = report_directory / "data_quality_after.json"
    _write_json(report_before_path, before_report)
    _write_json(report_after_path, after_report)
    manifest_path = report_directory / "source_manifest.csv"
    _write_manifest(manifest_path, manifest, source_ref)

    notebook_path = notebook_path or DEFAULT_NOTEBOOK_PATH
    profile_path_labels = {key: _workspace_path_label(value) for key, value in profile_paths.items()}
    if not raw_directory.is_relative_to(PROJECT_ROOT) and source_ref.startswith("main@"):
        if "+GoogleDrive:" in source_ref:
            raw_directory_label = f"{source_ref}:data/raw (main Git archive plus user-requested Google Drive ZIP; read-only)"
        else:
            raw_directory_label = f"{source_ref}:data/raw (read-only git archive)"
    else:
        raw_directory_label = _workspace_path_label(raw_directory)
    deliverables = {
        "cleaned_dataset": _workspace_path_label(dataset_path),
        "cleaning_notebook": _workspace_path_label(notebook_path),
        "quality_before": _workspace_path_label(report_before_path),
        "quality_after": _workspace_path_label(report_after_path),
        "final_report": _workspace_path_label(report_directory / "final_data_quality_report.md"),
        "cleaning_summary": _workspace_path_label(report_directory / "cleaning_summary.json"),
        "source_manifest": _workspace_path_label(manifest_path),
        "actual_salary_statistics": _workspace_path_label(stats_path),
        "salary_review_candidates": _workspace_path_label(salary_review_path),
        **profile_path_labels,
    }
    summary: dict[str, Any] = {
        "audit_date": audit_date.isoformat(),
        "source_ref": source_ref,
        "raw_data_directory": raw_directory_label,
        "cleaned_dataset_path": _workspace_path_label(dataset_path),
        "cleaned_dataset_sha256": dataset_hash,
        "scope": "partial_available_sources_only" if missing_required else "all_declared_sources_available",
        "missing_required_sources": missing_required,
        "available_job_source_count": source_files_used,
        "input_rows": input_rows,
        "output_rows": final_rows,
        "rows_dropped": input_rows - final_rows,
        "exact_duplicate_occurrences_retained": exact_duplicate_total,
        "duplicate_source_id_occurrences_retained": source_id_duplicate_occurrences,
        "possible_mojibake_records": possible_mojibake_records,
        "date_out_of_expected_range_records": date_out_of_range_records,
        "salary": after_report["salary"],
        "salary_policy": {
            **salary_policy,
            "fx_conversion_applied": bool(salary_policy.get("fx_rates_to_reporting_currency")),
            "annualization_factors": salary_policy.get("annualization_factors", {}),
            "approval_note": "Use only explicit, source-dated rates and user-approved period factors; no defaults are applied.",
        },
        "base_enriched_pair_audit": after_report["base_enriched_pair_audit"],
        "source_integrity": source_integrity,
        "sqlite_round_trip": sqlite_check,
        "existing_database_status": existing_database_status,
        "full_archive_analysis_status": (
            "not_rerun_missing_required_sources" if missing_required
            else "not_rerun_project_parquet_archive_or_database_unavailable" if archive_status != "available" or existing_database_status == "not_available_in_current_checkout"
            else "available_but_not_part_of_this_cleaning_run"
        ),
        "profile_outputs": profile_path_labels,
        "actual_salary_statistics_path": _workspace_path_label(stats_path),
        "deliverables": deliverables,
        "source_manifest": manifest,
        "file_reports": file_reports,
    }
    summary_path = report_directory / "cleaning_summary.json"
    _write_json(summary_path, summary)
    _write_markdown_report(report_directory / "final_data_quality_report.md", summary, before_report, after_report, file_reports, actual_stats)
    if notebook_path is not None:
        write_cleaning_notebook(notebook_path, summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-data-directory", type=Path, default=DEFAULT_RAW_DIRECTORY, help="Directory holding unchanged raw sources")
    parser.add_argument("--dataset-output", type=Path, default=DEFAULT_DATASET_PATH, help="Path for the compressed cleaned CSV")
    parser.add_argument("--report-directory", type=Path, default=DEFAULT_REPORT_DIRECTORY, help="Directory for quality, salary, and profile reports")
    parser.add_argument("--source-ref", default="unspecified", help="Source revision label, e.g. main@<commit>")
    parser.add_argument("--as-of-date", type=dt.date.fromisoformat, default=dt.datetime.now(dt.timezone.utc).date(), help="Date used only to flag obviously old/future timestamps (YYYY-MM-DD)")
    parser.add_argument("--salary-policy-file", type=Path, default=None, help="Optional explicit currency/annualization policy JSON; no conversion is done without one")
    parser.add_argument("--require-all-sources", action="store_true", help="Fail instead of producing an explicitly partial result when a declared source is missing")
    parser.add_argument("--notebook-output", type=Path, default=DEFAULT_NOTEBOOK_PATH, help="Path for the reproducible cleaning notebook")
    args = parser.parse_args(argv)

    summary = run_pipeline(
        args.raw_data_directory,
        args.dataset_output,
        args.report_directory,
        source_ref=args.source_ref,
        as_of_date=args.as_of_date,
        salary_policy_file=args.salary_policy_file,
        require_all_sources=args.require_all_sources,
        notebook_path=args.notebook_output,
    )
    print(json.dumps({
        "scope": summary["scope"],
        "input_rows": summary["input_rows"],
        "output_rows": summary["output_rows"],
        "rows_dropped": summary["rows_dropped"],
        "missing_required_sources": summary["missing_required_sources"],
        "salary": summary["salary"],
        "sqlite_round_trip": summary["sqlite_round_trip"],
        "source_integrity": summary["source_integrity"],
        "deliverables": summary["deliverables"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
