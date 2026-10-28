#!/usr/bin/env python3
"""Apply transparent salary estimates and run full, loss-preserving quality checks.

This is the second stage of run_full_cleaning_audit.py. The source-derived audit
CSV remains the staging input; only new derived columns are added. No source salary,
row, duplicate, outlier, or skill token is overwritten or removed.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import difflib
import gzip
import hashlib
import json
import math
import os
import re
import sqlite3
import statistics
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit, urlunsplit

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIRECTORY = PROJECT_ROOT / "scripts" / "data_cleaning"
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

import build_cleaning_audit as cleaner  # noqa: E402
import build_site_data as source_reader  # noqa: E402

DEFAULT_FX_POLICY = PROJECT_ROOT / "data" / "reference" / "fx_rates_2026-10-28.json"
DEFAULT_DATASET = PROJECT_ROOT / "data" / "processed" / "jobs_cleaned_audited.csv.gz"
DEFAULT_REPORT_DIRECTORY = PROJECT_ROOT / "analysis" / "reports" / "data_cleaning"

ADDED_FIELDS = [
    "salary_original",
    "salary_source_value_type",
    "salary_estimation_status",
    "salary_estimate_currency_code",
    "salary_estimation_method",
    "salary_estimation_source",
    "salary_estimation_confidence",
    "salary_estimate_reference_count",
    "salary_estimation_as_of_date",
    "salary_annualized_midpoint_reporting_currency",
    "salary_annual_min_usd",
    "salary_annual_salary_usd",
    "salary_annual_max_usd",
    "salary_annual_min_egp",
    "salary_annual_salary_egp",
    "salary_annual_max_egp",
    "salary_annual_min_sar",
    "salary_annual_salary_sar",
    "salary_annual_max_sar",
    "salary_estimate_range_basis",
    "role_family",
    "seniority_band",
    "location_clean",
    "location_key",
    "work_mode_standardized",
    "employment_type_standardized",
]

ROLE_FAMILY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("cybersecurity", ("cyber security", "cybersecurity", "information security", "infosec", "security analyst", "security engineer", "penetration tester", "soc analyst", "threat analyst", "security operations")),
    ("data_engineering", ("data engineer", "analytics engineer", "etl developer", "etl engineer", "data warehouse", "big data", "database administrator", "database engineer", "dba ")),
    ("data_science_ai_ml", ("data scientist", "machine learning", " ml engineer", "ai engineer", "artificial intelligence", "nlp engineer", "deep learning", "research scientist", "computer vision")),
    ("data_analytics_bi", ("data analyst", "business intelligence", " bi analyst", "bi developer", "reporting analyst", "analytics analyst", "power bi", "tableau developer")),
    ("software_engineering", ("software engineer", "software developer", "full stack", "full-stack", "frontend", "front-end", "backend", "back-end", "web developer", "mobile developer", "ios developer", "android developer", "application developer", "programmer", "java developer", ".net developer", "python developer")),
    ("cloud_devops_platform", ("devops", "site reliability", "sre ", "cloud engineer", "cloud architect", "platform engineer", "infrastructure engineer", "kubernetes", "systems engineer", "release engineer")),
    ("qa_testing", ("quality assurance", "qa engineer", "qa analyst", "test engineer", "software tester", "automation tester", "test automation")),
    ("network_it_support", ("network engineer", "network administrator", "systems administrator", "system administrator", "it support", "help desk", "service desk", "desktop support", "technical support", "network technician")),
    ("product_management", ("product manager", "product owner", "product management")),
    ("project_program_management", ("project manager", "program manager", "programme manager", "scrum master", "delivery manager", "project coordinator")),
    ("business_systems_analysis", ("business analyst", "systems analyst", "business systems", "functional consultant", "erp consultant", "sap consultant")),
    ("ux_ui_design", ("ux designer", "ui designer", "product designer", "user experience", "user interface", "interaction designer", "graphic designer")),
    ("sales_marketing", ("sales representative", "account executive", "sales engineer", "marketing manager", "digital marketing", "growth marketer", "technical recruiter")),
    ("hardware_embedded_iot", ("embedded", "firmware", "hardware engineer", "electronics engineer", "iot engineer", "robotics engineer", "electrical engineer")),
    ("engineering_other", ("engineer", "engineering technician", "technical architect")),
]

DATE_NAME_PARTS = ("date", "time", "timestamp", "posted", "publish", "updated", "modified", "collect", "scrap", "crawl", "ingest", "import")
COLLECTION_DATE_NAMES = (
    "collected_at", "source_collected_at", "collected_date", "date_collected", "scraped_at",
    "scraped_date", "crawl_date", "crawled_at", "ingested_at", "imported_at",
)

RAW_LOGICAL_FIELD_SPECS: list[tuple[str, tuple[str, ...], str]] = [
    ("title", ("title", "job_title", "job_title_short"), "high"),
    ("company", ("company", "company_name"), "medium"),
    ("country", ("country", "job_country"), "high"),
    ("description", ("description", "job_description", "description_text"), "medium"),
    ("source_url", ("link", "apply_url", "source_url", "job_url"), "medium"),
    ("skills", ("skills", "job_skills", "required_skills"), "high"),
    ("salary_original_text", ("salary", "salary_raw"), "high"),
    ("salary_any_numeric_source", ("salary", "salary_raw", "salary_range_est", "salary_local", "salary_usd", "salary_year_avg", "salary_hour_avg"), "high"),
    ("annualized_salary_usd", ("salary", "salary_raw", "salary_range_est", "salary_local", "salary_usd", "salary_year_avg", "salary_hour_avg"), "high"),
    ("publication_date", ("posted_at", "job_posted_date", "date_posted"), "medium"),
    ("source_update_date", ("updated", "source_updated_at"), "medium"),
    ("source_collection_date", COLLECTION_DATE_NAMES, "medium"),
]

OUTPUT_LOGICAL_FIELD_SPECS: dict[str, tuple[str, str]] = {
    "title": ("title_clean", "high"),
    "company": ("company_clean", "medium"),
    "country": ("country_standardized", "high"),
    "description": ("description_raw", "medium"),
    "source_url": ("source_url_raw", "medium"),
    "skills": ("skills_raw", "high"),
    "salary_original_text": ("salary_original", "high"),
    "salary_any_numeric_source": ("salary_source_value_type", "high"),
    "annualized_salary_usd": ("salary_annual_salary_usd", "high"),
    "publication_date": ("posted_at_iso", "medium"),
    "source_update_date": ("source_updated_at_iso", "medium"),
    "source_collection_date": ("source_collected_at_iso", "medium"),
}

TYPE_INTEGER_FIELDS = {
    "source_row_number", "description_char_count", "experience_years_min", "experience_years_max",
    "skill_token_count_raw", "skill_token_count_unique", "skill_canonical_id_count",
    "skill_duplicate_token_count", "salary_estimate_reference_count",
}
TYPE_BOOLEAN_FIELDS = {
    "exact_duplicate_within_source", "source_record_id_duplicate_occurrence",
    "encoding_suspected_mojibake", "salary_statistics_eligible",
}
TYPE_JSON_FIELDS = {"source_row_json", "skills_tokens_json", "skill_ids_json"}
TYPE_DATE_FIELDS = {"posted_at_iso", "source_updated_at_iso", "source_collected_at_iso", "salary_estimation_as_of_date"}
TYPE_NUMERIC_SUFFIXES = (
    "_original_currency", "_native", "_reporting_currency", "_usd", "_egp", "_sar",
)


def _is_missing(value: Any, *, json_empty_is_missing: bool = False) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    if not text or text.casefold() in cleaner.EMPTY_TEXT:
        return True
    return json_empty_is_missing and text in {"[]", "{}"}


def _to_float(value: Any) -> float | None:
    if _is_missing(value):
        return None
    try:
        number = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _format_number(value: float | None) -> str:
    return cleaner.format_number(value)


def _normal_key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.replace("&", " and ")
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _role_family(title: str, category: str = "") -> str:
    text = f" {_normal_key(title)} { _normal_key(category) } "
    for family, phrases in ROLE_FAMILY_RULES:
        if any(_normal_key(phrase) in text for phrase in phrases):
            return family
    if _is_missing(title) and _is_missing(category):
        return "unknown_role"
    return "other_technology"


def _seniority_band(title: str, experience_raw: str = "", experience_min: str = "", experience_max: str = "") -> str:
    text = f" {_normal_key(title)} {_normal_key(experience_raw)} "
    if re.search(r"\b(intern|internship|trainee|apprentice)\b", text):
        return "intern"
    if re.search(r"\b(chief|cto|cio|ciso|vp|vice president|director|head of|executive)\b", text):
        return "executive_director"
    if re.search(r"\b(lead|principal|staff|distinguished)\b", text):
        return "lead_principal"
    if re.search(r"\b(senior|sr)\b", text):
        return "senior"
    if re.search(r"\b(junior|jr|entry level|entry-level|graduate|new grad)\b", text):
        return "entry_junior"
    low = _to_float(experience_min)
    high = _to_float(experience_max)
    if low is not None:
        if low <= 2:
            return "entry_junior"
        if high is not None and high <= 5:
            return "mid"
        if low >= 6:
            return "senior"
    return "unspecified"


def _standardize_work_mode(raw_value: str, remote_flag: str) -> str:
    value = _normal_key(raw_value)
    if any(term in value for term in ("remote", "work from home", "wfh", "telecommute", "distributed")):
        return "remote"
    if "hybrid" in value:
        return "hybrid"
    if any(term in value for term in ("on site", "onsite", "in office", "office based", "on premises")):
        return "on_site"
    flag = _normal_key(remote_flag)
    if flag in {"true", "yes", "1", "y"}:
        return "remote"
    if flag in {"false", "no", "0", "n"}:
        return "not_remote_explicit"
    return "unknown_or_unmapped"


def _standardize_employment_type(raw_value: str) -> str:
    value = _normal_key(raw_value)
    if not value:
        return "unknown_or_unmapped"
    if "intern" in value or "trainee" in value:
        return "internship"
    if any(term in value for term in ("freelance", "freelancer", "self employed")):
        return "freelance"
    if any(term in value for term in ("contract", "contractor", "temporary", "temp")):
        return "contract_or_temporary"
    if "part time" in value or "parttime" in value:
        return "part_time"
    if "full time" in value or "fulltime" in value:
        return "full_time"
    if "permanent" in value:
        return "permanent"
    return "other_or_unmapped"


def _model_country(record: Mapping[str, str]) -> str:
    country = cleaner.collapse_whitespace(record.get("country_standardized", ""))
    if not country or record.get("location_scope") != "country_label_unverified":
        return ""
    return country.casefold()


def _benchmark_group_specs(record: Mapping[str, str], family: str, seniority: str) -> list[tuple[str, tuple[str, ...]]]:
    country = _model_country(record)
    title_key = _normal_key(record.get("title_key") or record.get("title_clean"))
    groups: list[tuple[str, tuple[str, ...]]] = []
    if country and title_key:
        groups.append(("exact_country_title", (country, title_key)))
    if country:
        groups.append(("country_family_seniority", (country, family, seniority)))
        groups.append(("country_family", (country, family)))
    groups.append(("global_family_seniority", (family, seniority)))
    groups.append(("global_family", (family,)))
    groups.append(("global_technology", ("all",)))
    return groups


def _model_group_key(method: str, values: tuple[str, ...]) -> tuple[str, ...]:
    return (method, *values)


def _benchmark_for_record(record: Mapping[str, str], models: Mapping[tuple[str, ...], list[float]]) -> dict[str, Any] | None:
    family = _role_family(record.get("title_clean", ""), record.get("category_raw", ""))
    seniority = _seniority_band(
        record.get("title_clean", ""), record.get("experience_raw", ""),
        record.get("experience_years_min", ""), record.get("experience_years_max", ""),
    )
    minimums = {
        "exact_country_title": 5,
        "country_family_seniority": 8,
        "country_family": 12,
        "global_family_seniority": 12,
        "global_family": 15,
        "global_technology": 25,
    }
    for method, values in _benchmark_group_specs(record, family, seniority):
        group_key = _model_group_key(method, values)
        points = models.get(group_key, [])
        if len(points) < minimums[method]:
            continue
        if method == "exact_country_title":
            confidence = "high" if len(points) >= 20 else "medium"
        elif method == "country_family_seniority":
            confidence = "medium" if len(points) >= 20 else "low_medium"
        elif method == "country_family":
            confidence = "low_medium" if len(points) >= 30 else "low"
        elif method == "global_family_seniority":
            confidence = "low"
        elif method == "global_family":
            confidence = "low"
        else:
            confidence = "very_low"
        return {
            "method": f"synthetic_{method}_median",
            "family": family,
            "seniority": seniority,
            "reference_count": len(points),
            "median_usd": statistics.median(points),
            "q1_usd": cleaner._quantile(points, 0.25),
            "q3_usd": cleaner._quantile(points, 0.75),
            "confidence": confidence,
            "group_key": group_key,
        }
    return None


def _annualized_native_salary(
    record: Mapping[str, str], annualization_factors: Mapping[str, float]
) -> tuple[float, float, float] | None:
    if record.get("salary_parse_status") not in {"parsed_single_amount", "parsed_range", "range_order_reversed"}:
        return None
    low = _to_float(record.get("salary_min_original_currency"))
    high = _to_float(record.get("salary_max_original_currency"))
    if low is None:
        low = _to_float(record.get("salary_amount_1_original_currency"))
    if high is None:
        high = _to_float(record.get("salary_amount_2_original_currency"))
    if low is None or high is None or low < 0 or high < 0:
        return None
    low, high = min(low, high), max(low, high)
    period = str(record.get("salary_period_code", "")).upper()
    factor = 1.0 if period == "YEAR" else annualization_factors.get(period)
    if factor is None or not math.isfinite(float(factor)) or float(factor) <= 0:
        return None
    factor = float(factor)
    return low * factor, ((low + high) / 2.0) * factor, high * factor


def _actual_annual_usd(
    record: Mapping[str, str],
    fx_rates: Mapping[str, float],
    annualization_factors: Mapping[str, float],
) -> tuple[float, float, float] | None:
    native = _annualized_native_salary(record, annualization_factors)
    currency = str(record.get("salary_currency_code", "")).upper()
    rate = fx_rates.get(currency)
    if native is None or rate is None:
        return None
    low, midpoint, high = native
    rate = float(rate)
    if low < 0 or high < low or midpoint < low or midpoint > high or not math.isfinite(rate) or rate <= 0:
        return None
    return low * rate, midpoint * rate, high * rate


def _load_fx_policy(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("reporting_currency") != "USD":
        raise ValueError("Full audit currently requires USD as its base reporting currency.")
    rate_date = dt.date.fromisoformat(payload["fx_rate_date"])
    rates = {str(code).upper(): float(rate) for code, rate in payload.get("fx_rates_to_reporting_currency", {}).items()}
    if "USD" not in rates or not math.isclose(rates["USD"], 1.0):
        raise ValueError("The FX policy must contain USD=1.0.")
    if any(not math.isfinite(rate) or rate <= 0 for rate in rates.values()):
        raise ValueError("All exchange rates must be finite and positive.")
    annualization = {str(k).upper(): float(v) for k, v in payload.get("annualization_factors", {}).items()}
    expected = {"MONTH": 12.0, "WEEK": 52.0, "DAY": 260.0, "HOUR": 2080.0}
    if annualization != expected:
        raise ValueError(f"Annualization factors differ from documented defaults: {annualization!r}")
    target_rates = {str(code).upper(): float(rate) for code, rate in payload.get("target_currency_rates_from_usd", {}).items()}
    if not {"EGP", "SAR"}.issubset(target_rates):
        raise ValueError("The FX policy must define USD-to-EGP and USD-to-SAR target rates.")
    if any(not math.isfinite(rate) or rate <= 0 for rate in target_rates.values()):
        raise ValueError("Target-currency rates must be finite and positive.")
    details = payload.get("currency_rate_details", {})
    if set(rates) != {str(code).upper() for code in details}:
        raise ValueError("Currency rate details and USD conversion-rate codes must match exactly.")
    for code, detail in details.items():
        code = str(code).upper()
        if not isinstance(detail, dict) or not detail.get("reference") or not detail.get("source_url") or not detail.get("source_note"):
            raise ValueError(f"Currency rate {code} requires a reference, source URL, and source note.")
        detail_rate = _to_float(detail.get("usd_per_unit"))
        if detail_rate is None or not math.isclose(detail_rate, rates[code], rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError(f"Currency rate {code} does not match its documented usd_per_unit value.")
        if not str(detail["source_url"]).startswith("https://"):
            raise ValueError(f"Currency rate {code} must use an HTTPS source URL.")
    target_details = payload.get("target_currency_rate_details", {})
    for code in ("EGP", "SAR"):
        if code not in rates or not math.isclose(rates[code] * target_rates[code], 1.0, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError(f"USD-to-{code} target rate is inconsistent with the inverse source-currency rate.")
        detail = target_details.get(code, {})
        if not isinstance(detail, dict) or not detail.get("reference") or not detail.get("source_url") or not detail.get("source_note"):
            raise ValueError(f"Target-currency rate {code} requires a reference, source URL, and source note.")
        documented_target_rate = _to_float(detail.get("local_units_per_usd"))
        if documented_target_rate is None or not math.isclose(documented_target_rate, target_rates[code], rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError(f"Target-currency rate {code} does not match its documented local_units_per_usd value.")
        if not str(detail["source_url"]).startswith("https://"):
            raise ValueError(f"Target-currency rate {code} must use an HTTPS source URL.")
    return {
        **payload,
        "fx_rates_to_reporting_currency": rates,
        "target_currency_rates_from_usd": target_rates,
        "annualization_factors": annualization,
        "fx_rate_date": rate_date.isoformat(),
    }


def _build_benchmarks(
    dataset_path: Path, fx_policy: Mapping[str, Any]
) -> tuple[dict[tuple[str, ...], list[float]], dict[str, Any]]:
    models: dict[tuple[str, ...], list[float]] = defaultdict(list)
    training_count_by_source: Counter[str] = Counter()
    training_count_by_currency: Counter[str] = Counter()
    fx_rates = fx_policy["fx_rates_to_reporting_currency"]
    annualization_factors = fx_policy["annualization_factors"]
    with gzip.open(dataset_path, "rt", encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            if record.get("salary_value_type") != "actual_reported" or record.get("salary_statistics_eligible") != "yes":
                continue
            currency = str(record.get("salary_currency_code", "")).upper()
            if currency not in fx_rates:
                continue
            normalized = _actual_annual_usd(record, fx_rates, annualization_factors)
            if normalized is None:
                continue
            low, midpoint, high = normalized
            if midpoint <= 0 or not all(math.isfinite(value) for value in (low, midpoint, high)):
                continue
            family = _role_family(record.get("title_clean", ""), record.get("category_raw", ""))
            seniority = _seniority_band(
                record.get("title_clean", ""), record.get("experience_raw", ""),
                record.get("experience_years_min", ""), record.get("experience_years_max", ""),
            )
            for method, values in _benchmark_group_specs(record, family, seniority):
                models[_model_group_key(method, values)].append(midpoint)
            training_count_by_source[record.get("source_dataset", "")] += 1
            training_count_by_currency[currency] += 1
    model_summary = {
        "benchmark_actual_record_count": sum(training_count_by_source.values()),
        "benchmark_count_by_source": dict(training_count_by_source),
        "benchmark_count_by_currency": dict(training_count_by_currency),
        "benchmark_group_count": len(models),
        "benchmark_eligibility_policy": "Only salary_value_type=actual_reported records with salary_statistics_eligible=yes, explicit currency and recognized pay period, and a valid positive annual USD midpoint train the model. Synthetic and legacy estimates are excluded; scale-review records remain in the dataset but not in references.",
        "outlier_policy": "IQR outliers within the eligible actual reference pool are retained; medians are used for robustness. No source row is deleted."
    }
    return models, model_summary


def _salary_values_for_output(record: Mapping[str, str], fx_policy: Mapping[str, Any]) -> dict[str, str]:
    fx_rates = fx_policy["fx_rates_to_reporting_currency"]
    target_rates = fx_policy["target_currency_rates_from_usd"]
    annualization_factors = fx_policy["annualization_factors"]
    values = {field: "" for field in (
        "salary_annualized_min_native", "salary_annualized_max_native", "salary_annualized_midpoint_native",
        "salary_reporting_currency", "salary_fx_rate_to_reporting_currency", "salary_fx_rate_source", "salary_fx_rate_date",
        "salary_annualized_min_reporting_currency", "salary_annualized_max_reporting_currency",
        "salary_annualized_midpoint_reporting_currency",
        "salary_annual_min_usd", "salary_annual_salary_usd", "salary_annual_max_usd",
        "salary_annual_min_egp", "salary_annual_salary_egp", "salary_annual_max_egp",
        "salary_annual_min_sar", "salary_annual_salary_sar", "salary_annual_max_sar",
    )}
    native = _annualized_native_salary(record, annualization_factors)
    currency = str(record.get("salary_currency_code", "")).upper()
    rate = fx_rates.get(currency)
    if native is not None:
        low_native, mid_native, high_native = native
        values.update({
            "salary_annualized_min_native": _format_number(low_native),
            "salary_annualized_max_native": _format_number(high_native),
            "salary_annualized_midpoint_native": _format_number(mid_native),
        })
    if rate is None:
        return values
    detail = fx_policy["currency_rate_details"][currency]
    rate = float(rate)
    values.update({
        "salary_reporting_currency": "USD",
        "salary_fx_rate_to_reporting_currency": _format_number(rate),
        "salary_fx_rate_source": str(detail["source_note"]),
        "salary_fx_rate_date": str(fx_policy["fx_rate_date"]),
    })
    if native is None:
        return values
    low_native, mid_native, high_native = native
    low_usd, mid_usd, high_usd = low_native * rate, mid_native * rate, high_native * rate
    egp_rate = float(target_rates["EGP"])
    sar_rate = float(target_rates["SAR"])
    values.update({
        "salary_annualized_min_reporting_currency": _format_number(low_usd),
        "salary_annualized_max_reporting_currency": _format_number(high_usd),
        "salary_annualized_midpoint_reporting_currency": _format_number(mid_usd),
        "salary_annual_min_usd": _format_number(low_usd),
        "salary_annual_salary_usd": _format_number(mid_usd),
        "salary_annual_max_usd": _format_number(high_usd),
        "salary_annual_min_egp": _format_number(low_usd * egp_rate),
        "salary_annual_salary_egp": _format_number(mid_usd * egp_rate),
        "salary_annual_max_egp": _format_number(high_usd * egp_rate),
        "salary_annual_min_sar": _format_number(low_usd * sar_rate),
        "salary_annual_salary_sar": _format_number(mid_usd * sar_rate),
        "salary_annual_max_sar": _format_number(high_usd * sar_rate),
    })
    return values


def _append_flag(value: str, flag: str) -> str:
    return ";".join(dict.fromkeys(part for part in [*(value or "").split(";"), flag] if part))


def _selected_original_salary(record: Mapping[str, str]) -> str:
    candidate = record.get("salary_candidate_raw", "")
    raw = record.get("salary_raw", "")
    return candidate if not _is_missing(candidate) else raw


def _parse_date_class(field_name: str) -> str:
    name = field_name.casefold()
    if any(part in name for part in ("collect", "scrap", "crawl", "ingest", "import")):
        return "collection_date"
    if any(part in name for part in ("posted", "publish")):
        return "publication_date"
    if any(part in name for part in ("updated", "modified")):
        return "update_date"
    return "other_date_like"


def _infer_source_value_type(value: str, field_name: str) -> str:
    if _is_missing(value):
        return "missing"
    text = str(value).strip()
    lower = text.casefold()
    if lower in {"true", "false", "yes", "no", "y", "n"}:
        return "boolean_like_text"
    if any(part in field_name.casefold() for part in DATE_NAME_PARTS) and cleaner.parse_source_datetime(text):
        return "date_time_like_text"
    try:
        number = float(text.replace(",", ""))
        if math.isfinite(number):
            return "integer_like_text" if number.is_integer() else "decimal_like_text"
    except ValueError:
        pass
    if text[:1] in "[{":
        try:
            json.loads(text)
            return "json_like_text"
        except (ValueError, TypeError):
            pass
    return "text_or_mixed_text"


def _expected_output_type(field_name: str) -> str:
    if field_name in TYPE_JSON_FIELDS:
        return "JSON object" if field_name == "source_row_json" else "JSON array"
    if field_name in TYPE_BOOLEAN_FIELDS:
        return "boolean (yes/no)"
    if field_name in TYPE_INTEGER_FIELDS:
        return "integer"
    if field_name in TYPE_DATE_FIELDS:
        return "UTC ISO-8601 datetime/date"
    if field_name.endswith(("_min_original_currency", "_max_original_currency", "_midpoint_original_currency", "_amount_1_original_currency", "_amount_2_original_currency", "_annualized_min_native", "_annualized_max_native", "_annualized_midpoint_native", "_annualized_min_reporting_currency", "_annualized_max_reporting_currency", "_annualized_midpoint_reporting_currency", "_annual_min_usd", "_annual_salary_usd", "_annual_max_usd", "_annual_min_egp", "_annual_salary_egp", "_annual_max_egp", "_annual_min_sar", "_annual_salary_sar", "_annual_max_sar", "_fx_rate_to_reporting_currency")):
        return "finite numeric"
    return "text/category/string"


def _validate_output_value(field_name: str, value: str) -> bool:
    if _is_missing(value, json_empty_is_missing=False):
        return True
    expected = _expected_output_type(field_name)
    if expected == "JSON object":
        try:
            return isinstance(json.loads(value), dict)
        except (ValueError, TypeError):
            return False
    if expected == "JSON array":
        try:
            return isinstance(json.loads(value), list)
        except (ValueError, TypeError):
            return False
    if expected == "boolean (yes/no)":
        return value.casefold() in {"yes", "no"}
    if expected == "integer":
        try:
            int(value)
            return True
        except ValueError:
            return False
    if expected == "UTC ISO-8601 datetime/date":
        if field_name == "salary_estimation_as_of_date":
            try:
                dt.date.fromisoformat(value)
                return True
            except ValueError:
                return False
        try:
            cleaner.parse_source_datetime(value)
            return bool(cleaner.parse_source_datetime(value))
        except (ValueError, OverflowError):
            return False
    if expected == "finite numeric":
        return _to_float(value) is not None
    return True


def _raw_source_audit(raw_directory: Path, as_of_date: dt.date) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    source_specs = {item["file"]: item for item in cleaner.JOB_SOURCE_SPECS}
    source_specs.update({name: {"file": name, "dataset": "reference_only", "kind": "csv"} for name in cleaner.BASE_EXPORTS.values()})
    coverage: list[dict[str, Any]] = []
    type_audit: list[dict[str, Any]] = []
    date_audit: list[dict[str, Any]] = []
    summary: dict[str, Any] = {"files": {}, "collection_date_source_columns": [], "all_selected_sources_present": True}

    for filename in cleaner.ALL_EXPECTED_FILES:
        path = raw_directory / filename
        spec = source_specs[filename]
        if not path.is_file():
            summary["files"][filename] = {"rows": 0, "status": "missing"}
            if spec.get("required"):
                summary["all_selected_sources_present"] = False
            continue
        column_nonempty: Counter[str] = Counter()
        column_types: dict[str, Counter[str]] = defaultdict(Counter)
        date_columns: dict[str, dict[str, Any]] = {}
        row_count = 0
        with cleaner._open_source_rows(path, spec["kind"]) as rows:
            for row in rows:
                row_count += 1
                for field_name, value in row.items():
                    text = "" if value is None else str(value)
                    if not _is_missing(text):
                        column_nonempty[field_name] += 1
                    column_types[field_name][_infer_source_value_type(text, field_name)] += 1
                    if any(part in field_name.casefold() for part in DATE_NAME_PARTS):
                        detail = date_columns.setdefault(field_name, {
                            "field_name": field_name,
                            "date_class": _parse_date_class(field_name),
                            "present": 0,
                            "missing": 0,
                            "parseable": 0,
                            "unparseable": 0,
                            "before_2000": 0,
                            "after_audit_date": 0,
                            "earliest": "",
                            "latest": "",
                        })
                        if _is_missing(text):
                            detail["missing"] += 1
                        else:
                            detail["present"] += 1
                            parsed = cleaner.parse_source_datetime(text)
                            if parsed is None:
                                detail["unparseable"] += 1
                            else:
                                detail["parseable"] += 1
                                iso = cleaner.date_to_iso(parsed)
                                detail["earliest"] = min(detail["earliest"], iso) if detail["earliest"] else iso
                                detail["latest"] = max(detail["latest"], iso) if detail["latest"] else iso
                                if parsed.date() < dt.date(2000, 1, 1):
                                    detail["before_2000"] += 1
                                if parsed.date() > as_of_date:
                                    detail["after_audit_date"] += 1
        columns = sorted(column_types)
        for field_name in columns:
            present = int(column_nonempty[field_name])
            missing = row_count - present
            coverage.append({
                "source_file": filename,
                "source_dataset": spec.get("dataset", "reference_only"),
                "field_name": field_name,
                "rows_in_source": row_count,
                "present_count": present,
                "missing_count": missing,
                "missing_percent": round(100.0 * missing / row_count, 4) if row_count else "",
                "physical_reader_type": "text/string (CSV/XLSX reader stringifies source cells)",
            })
            counts = column_types[field_name]
            observed = {key: value for key, value in sorted(counts.items()) if value}
            nonmissing_types = {key: value for key, value in observed.items() if key != "missing"}
            inferred = "all missing" if not nonmissing_types else "mixed: " + ", ".join(nonmissing_types)
            type_audit.append({
                "source_file": filename,
                "source_dataset": spec.get("dataset", "reference_only"),
                "field_name": field_name,
                "rows_in_source": row_count,
                "nonmissing_count": present,
                "missing_count": missing,
                "logical_value_shapes": json.dumps(observed, ensure_ascii=False, sort_keys=True),
                "inferred_shape_summary": inferred,
                "review_note": "Source cells are preserved as strings; numeric/date coercion is performed only in typed derived columns.",
            })
        for detail in date_columns.values():
            date_audit.append({
                "stage": "raw_source",
                "source_file": filename,
                **detail,
                "missing_percent": round(100.0 * detail["missing"] / row_count, 4) if row_count else "",
            })
            if detail["date_class"] == "collection_date" and detail["present"]:
                summary["collection_date_source_columns"].append({"source_file": filename, "field_name": detail["field_name"], "nonmissing": detail["present"]})
        summary["files"][filename] = {"rows": row_count, "columns": len(columns), "status": "available"}

    return coverage, type_audit, date_audit, summary


def _source_logical_presence(row: Mapping[str, Any], field_name: str) -> bool:
    spec = next((entry for entry in RAW_LOGICAL_FIELD_SPECS if entry[0] == field_name), None)
    if spec is None:
        return False
    _, candidates, _ = spec
    if field_name == "salary_any_numeric_source":
        return any(source_reader.contains_numeric_salary_amount(cleaner.raw_field(row, key)) for key in candidates)
    return bool(cleaner.source_value(row, *candidates))


def _write_logical_coverage(
    raw_directory: Path,
    dataset_path: Path,
    path: Path,
    as_of_date: dt.date,
) -> dict[str, Any]:
    raw_counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    source_specs = {item["file"]: item for item in cleaner.JOB_SOURCE_SPECS}
    raw_rows: Counter[str] = Counter()
    for spec in cleaner.JOB_SOURCE_SPECS:
        source_path = raw_directory / spec["file"]
        if not source_path.is_file():
            continue
        with cleaner._open_source_rows(source_path, spec["kind"]) as rows:
            for row in rows:
                raw_rows[spec["file"]] += 1
                for field_name, _, _ in RAW_LOGICAL_FIELD_SPECS:
                    if _source_logical_presence(row, field_name):
                        raw_counts[(spec["file"], field_name)]["present"] += 1
    output_counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    output_rows: Counter[str] = Counter()
    with gzip.open(dataset_path, "rt", encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            source_file = record.get("source_file", "")
            output_rows[source_file] += 1
            for logical, (column, _) in OUTPUT_LOGICAL_FIELD_SPECS.items():
                if logical == "salary_any_numeric_source":
                    present = record.get("salary_parse_status", "") in {"parsed_single_amount", "parsed_range", "range_order_reversed"} or record.get("salary_value_type") == "estimated_synthetic"
                else:
                    present = not _is_missing(record.get(column, ""))
                if present:
                    output_counts[(source_file, logical)]["present"] += 1
    rows: list[dict[str, Any]] = []
    for spec in cleaner.JOB_SOURCE_SPECS:
        filename = spec["file"]
        total_before = raw_rows[filename]
        total_after = output_rows[filename]
        for logical, _, impact in RAW_LOGICAL_FIELD_SPECS:
            before_present = raw_counts[(filename, logical)]["present"]
            after_present = output_counts[(filename, logical)]["present"]
            after_column, _ = OUTPUT_LOGICAL_FIELD_SPECS[logical]
            rows.append({
                "source_file": filename,
                "source_dataset": spec["dataset"],
                "logical_field": logical,
                "before_source_column_aliases": ";".join(next(entry[1] for entry in RAW_LOGICAL_FIELD_SPECS if entry[0] == logical)),
                "after_clean_column": after_column,
                "rows_before": total_before,
                "before_present": before_present,
                "before_missing": max(0, total_before - before_present),
                "before_missing_percent": round(100.0 * (total_before - before_present) / total_before, 4) if total_before else "",
                "rows_after": total_after,
                "after_present": after_present,
                "after_missing": max(0, total_after - after_present),
                "after_missing_percent": round(100.0 * (total_after - after_present) / total_after, 4) if total_after else "",
                "high_impact_if_missing": impact,
                "note": "Raw source values remain available in source_row_json and *_raw fields; coverage changes do not imply source-value replacement.",
            })
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = list(rows[0]) if rows else []
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return {
        "rows_before": sum(raw_rows.values()),
        "rows_after": sum(output_rows.values()),
        "raw_rows_by_file": dict(raw_rows),
        "output_rows_by_file": dict(output_rows),
    }


def _source_row_fingerprint(record: Mapping[str, str]) -> str:
    raw = record.get("source_row_json", "")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest() if raw else ""


def _normalized_url(value: str) -> str:
    if not value:
        return ""
    try:
        parts = urlsplit(value.strip())
        if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
            return ""
        path = re.sub(r"/+", "/", parts.path).rstrip("/")
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))
    except ValueError:
        return ""


def _duplicate_review_audit(dataset_path: Path, report_directory: Path) -> dict[str, Any]:
    database_path = report_directory / ".duplicate_review_work.sqlite3"
    if database_path.exists():
        database_path.unlink()
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA temp_store=FILE")
    connection.execute("""CREATE TABLE job_meta (
        record_id TEXT NOT NULL,
        source_file TEXT NOT NULL,
        source_row_number TEXT NOT NULL,
        source_record_id TEXT NOT NULL,
        title TEXT NOT NULL,
        title_norm TEXT NOT NULL,
        company TEXT NOT NULL,
        company_norm TEXT NOT NULL,
        country TEXT NOT NULL,
        country_norm TEXT NOT NULL,
        location TEXT NOT NULL,
        location_norm TEXT NOT NULL,
        url_norm TEXT NOT NULL,
        salary_norm TEXT NOT NULL,
        posted_at TEXT NOT NULL,
        raw_hash TEXT NOT NULL,
        salary_usd REAL,
        salary_type TEXT NOT NULL
    )""")
    with gzip.open(dataset_path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        batch: list[tuple[Any, ...]] = []
        for record in reader:
            title = record.get("title_clean", "")
            company = record.get("company_clean", "")
            country = record.get("country_standardized", "")
            location = record.get("location_clean", "")
            original_salary = _selected_original_salary(record)
            annual = _to_float(record.get("salary_annual_salary_usd")) if record.get("salary_source_value_type") == "actual_reported" else None
            batch.append((
                record.get("record_id", ""), record.get("source_file", ""), record.get("source_row_number", ""),
                record.get("source_record_id", ""), title, _normal_key(title), company, _normal_key(company),
                country, _normal_key(country), location, _normal_key(location), _normalized_url(record.get("source_url_raw", "")),
                _normal_key(original_salary), record.get("posted_at_iso", ""), _source_row_fingerprint(record),
                annual, record.get("salary_source_value_type", ""),
            ))
            if len(batch) >= 5000:
                connection.executemany("INSERT INTO job_meta VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
                batch.clear()
        if batch:
            connection.executemany("INSERT INTO job_meta VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
    connection.commit()
    connection.executescript("""
        CREATE INDEX ix_job_url ON job_meta(url_norm);
        CREATE INDEX ix_job_raw_hash ON job_meta(raw_hash);
        CREATE INDEX ix_job_signature ON job_meta(title_norm, company_norm, country_norm, location_norm, salary_norm, posted_at);
        CREATE INDEX ix_job_near_block ON job_meta(company_norm, country_norm, location_norm);
    """)
    output_path = report_directory / "duplicate_review_candidates.csv"
    fields = [
        "candidate_id", "match_type", "match_rule", "record_count", "source_files_json",
        "record_ids_json", "titles_json", "similarity", "review_status",
    ]
    exact_groups: list[dict[str, Any]] = []

    def add_group(match_type: str, match_rule: str, key_columns: str, where_clause: str, source_fields: tuple[Any, ...] = ()) -> None:
        query = f"SELECT {key_columns}, COUNT(*) AS n, COUNT(DISTINCT source_file) AS source_count FROM job_meta {where_clause} GROUP BY {key_columns} HAVING n > 1 AND source_count > 1"
        for group in connection.execute(query, source_fields):
            key_len = len(group) - 2
            key = tuple(group[:key_len])
            clauses = " AND ".join(f"{column} IS ?" for column in key_columns.split(", "))
            records = connection.execute(
                f"SELECT record_id, source_file, title FROM job_meta WHERE {clauses} ORDER BY source_file, record_id",
                key,
            ).fetchall()
            exact_groups.append({
                "candidate_id": "dup-" + hashlib.sha1((match_type + json.dumps(key, ensure_ascii=False)).encode("utf-8")).hexdigest()[:16],
                "match_type": match_type,
                "match_rule": match_rule,
                "record_count": len(records),
                "source_files_json": json.dumps(sorted({item[1] for item in records}), ensure_ascii=False),
                "record_ids_json": json.dumps([item[0] for item in records], ensure_ascii=False),
                "titles_json": json.dumps([item[2] for item in records], ensure_ascii=False),
                "similarity": "1.0",
                "review_status": "candidate_only_retained_not_merged",
            })

    add_group("cross_source_exact_raw_row", "same SHA-256 of preserved source_row_json", "raw_hash", "WHERE raw_hash != ''")
    add_group("cross_source_exact_url", "same normalized HTTP(S) URL after removing query and fragment", "url_norm", "WHERE url_norm != ''")
    add_group(
        "cross_source_exact_listing_signature",
        "same normalized title, company, country, location, selected raw salary text, and explicit posting date",
        "title_norm, company_norm, country_norm, location_norm, salary_norm, posted_at",
        "WHERE title_norm != '' AND company_norm != '' AND (location_norm != '' OR country_norm != '')",
    )

    near_candidates: list[dict[str, Any]] = []
    skipped_large_blocks = 0
    evaluated_pairs = 0
    block_cursor = connection.execute("""
        SELECT company_norm, country_norm, location_norm, COUNT(*) AS n
        FROM job_meta
        WHERE company_norm != '' AND country_norm != '' AND location_norm != ''
        GROUP BY company_norm, country_norm, location_norm
        HAVING n > 1
    """)
    for company_norm, country_norm, location_norm, block_count in block_cursor:
        if block_count > 60:
            skipped_large_blocks += 1
            continue
        records = connection.execute(
            "SELECT record_id, source_file, title, title_norm, salary_norm, posted_at, salary_usd, salary_type "
            "FROM job_meta WHERE company_norm=? AND country_norm=? AND location_norm=? ORDER BY source_file, record_id",
            (company_norm, country_norm, location_norm),
        ).fetchall()
        for index, first in enumerate(records):
            for second in records[index + 1:]:
                if first[1] == second[1] or not first[3] or not second[3] or first[3] == second[3]:
                    continue
                evaluated_pairs += 1
                similarity = difflib.SequenceMatcher(None, first[3], second[3], autojunk=False).ratio()
                if similarity < 0.90:
                    continue
                salary_compatible = bool(first[4] and first[4] == second[4])
                if first[6] is not None and second[6] is not None and first[7] == second[7] == "actual_reported":
                    denominator = max(abs(first[6]), abs(second[6]), 1.0)
                    salary_compatible = salary_compatible or abs(first[6] - second[6]) / denominator <= 0.05
                same_posting_date = bool(first[5] and first[5] == second[5])
                if not (salary_compatible or same_posting_date):
                    continue
                pair_key = f"{first[0]}|{second[0]}"
                near_candidates.append({
                    "candidate_id": "near-" + hashlib.sha1(pair_key.encode("utf-8")).hexdigest()[:16],
                    "match_type": "cross_source_near_duplicate",
                    "match_rule": "same normalized company/country/location; title SequenceMatcher >= 0.90; salary text/actual annual pay within 5% or explicit posting date matches",
                    "record_count": 2,
                    "source_files_json": json.dumps(sorted({first[1], second[1]}), ensure_ascii=False),
                    "record_ids_json": json.dumps([first[0], second[0]], ensure_ascii=False),
                    "titles_json": json.dumps([first[2], second[2]], ensure_ascii=False),
                    "similarity": round(similarity, 4),
                    "review_status": "candidate_only_retained_not_merged",
                })
    all_candidates = exact_groups + near_candidates
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(all_candidates)
    exact_raw_count = sum(row["match_type"] == "cross_source_exact_raw_row" for row in exact_groups)
    exact_url_count = sum(row["match_type"] == "cross_source_exact_url" for row in exact_groups)
    exact_signature_count = sum(row["match_type"] == "cross_source_exact_listing_signature" for row in exact_groups)
    connection.close()
    database_path.unlink(missing_ok=True)
    return {
        "candidate_file": _workspace_path_label(output_path),
        "cross_source_exact_raw_row_groups": exact_raw_count,
        "cross_source_exact_url_groups": exact_url_count,
        "cross_source_exact_listing_signature_groups": exact_signature_count,
        "cross_source_near_duplicate_pairs": len(near_candidates),
        "near_duplicate_title_pairs_evaluated": evaluated_pairs,
        "large_near_duplicate_blocks_skipped_over_60_rows": skipped_large_blocks,
        "candidate_groups_total": len(all_candidates),
        "deleted_or_merged_rows": 0,
        "review_policy": "All cross-source candidates are retained; match signals are not proof that two listings are the same job.",
    }


def _write_plain_csv(path: Path, fields: list[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _workspace_path_label(path: Path) -> str:
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(resolved)


def _quality_pass(
    raw_directory: Path,
    dataset_path: Path,
    report_directory: Path,
    as_of_date: dt.date,
    fx_policy: Mapping[str, Any],
    models: Mapping[tuple[str, ...], list[float]],
    benchmark_report: Mapping[str, Any],
    database_validation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    raw_coverage, raw_types, raw_dates, raw_summary = _raw_source_audit(raw_directory, as_of_date)
    raw_column_path = report_directory / "raw_source_column_coverage.csv"
    _write_plain_csv(raw_column_path, ["source_file", "source_dataset", "field_name", "rows_in_source", "present_count", "missing_count", "missing_percent", "physical_reader_type"], raw_coverage)
    raw_type_path = report_directory / "raw_source_type_audit.csv"
    _write_plain_csv(raw_type_path, ["source_file", "source_dataset", "field_name", "rows_in_source", "nonmissing_count", "missing_count", "logical_value_shapes", "inferred_shape_summary", "review_note"], raw_types)
    logical_coverage_path = report_directory / "field_coverage_comparison.csv"
    logical_counts = _write_logical_coverage(raw_directory, dataset_path, logical_coverage_path, as_of_date)

    output_coverage: list[dict[str, Any]] = []
    output_type_rows: list[dict[str, Any]] = []
    output_counts: Counter[str] = Counter()
    output_by_file: dict[str, Counter[str]] = defaultdict(Counter)
    output_row_counts: Counter[str] = Counter()
    type_observed: dict[str, Counter[str]] = defaultdict(Counter)
    type_invalid: Counter[str] = Counter()
    typed_rows = 0
    source_row_ids: set[str] = set()
    duplicate_record_ids = 0
    salary_status_counts: Counter[str] = Counter()
    salary_value_type_counts: Counter[str] = Counter()
    salary_estimate_method_counts: Counter[str] = Counter()
    salary_currency_counts: Counter[str] = Counter()
    annual_salary_available_counts: Counter[str] = Counter()
    country_pairs: Counter[tuple[str, str]] = Counter()
    role_family_counts: Counter[tuple[str, str]] = Counter()
    skill_stats: Counter[str] = Counter()
    skill_alias_audit: dict[str, dict[str, Any]] = {}
    unique_skill_ids: set[str] = set()
    skill_alias_reference = cleaner._load_skill_reference()
    date_output_details: dict[tuple[str, str], dict[str, Any]] = {}
    actual_salary_groups: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    estimates_by_group: dict[tuple[str, str, str, str], Counter[str]] = defaultdict(Counter)
    consistency: Counter[str] = Counter()
    consistency_checked: Counter[str] = Counter()
    salary_rate_usd = fx_policy["fx_rates_to_reporting_currency"]
    target_rates = fx_policy["target_currency_rates_from_usd"]
    clean_dataset_temp = report_directory / ".full_column_coverage_work.csv"

    # Full type / coverage / relation pass. The checked record IDs fit comfortably in memory;
    # everything else is accumulated as compact counters and group statistics.
    with gzip.open(dataset_path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        all_fields = reader.fieldnames or []
        for record in reader:
            typed_rows += 1
            source_file = record.get("source_file", "")
            source_dataset = record.get("source_dataset", "")
            output_row_counts[source_file] += 1
            for field_name in all_fields:
                value = record.get(field_name, "") or ""
                json_empty = field_name in {"skills_tokens_json", "skill_ids_json"}
                if not _is_missing(value, json_empty_is_missing=json_empty):
                    output_counts[field_name] += 1
                    output_by_file[source_file][field_name] += 1
                    type_observed[field_name][_infer_source_value_type(value, field_name)] += 1
                if not _validate_output_value(field_name, value):
                    type_invalid[field_name] += 1
            record_id = record.get("record_id", "")
            if record_id in source_row_ids:
                duplicate_record_ids += 1
            else:
                source_row_ids.add(record_id)
            salary_status_counts[record.get("salary_estimation_status", "")] += 1
            salary_value_type_counts[record.get("salary_value_type", "")] += 1
            salary_estimate_method_counts[record.get("salary_estimation_method", "")] += 1
            if record.get("salary_currency_code"):
                salary_currency_counts[record["salary_currency_code"]] += 1
            if not _is_missing(record.get("salary_annual_salary_usd", "")):
                annual_salary_available_counts["USD"] += 1
            if not _is_missing(record.get("salary_annual_salary_egp", "")):
                annual_salary_available_counts["EGP"] += 1
            if not _is_missing(record.get("salary_annual_salary_sar", "")):
                annual_salary_available_counts["SAR"] += 1
            country_pairs[(record.get("country_raw", ""), record.get("country_standardized", ""))] += 1
            role_family_counts[(source_dataset, record.get("role_family", ""))] += 1
            for metric in ("salary_annual_salary_usd", "salary_annual_salary_egp", "salary_annual_salary_sar"):
                if not _is_missing(record.get(metric, "")):
                    estimates_by_group[(record.get("salary_estimation_method", ""), record.get("country_standardized", ""), record.get("role_family", ""), record.get("seniority_band", ""))][metric + "_count"] += 1
            # Skill field relationships are checked against the JSON representations.
            try:
                tokens = json.loads(record.get("skills_tokens_json", "[]") or "[]")
                skill_ids = json.loads(record.get("skill_ids_json", "[]") or "[]")
                consistency_checked["skill_json_counts"] += 1
                if len(tokens) != int(record.get("skill_token_count_unique") or 0):
                    consistency["skill_json_count_mismatch"] += 1
                if len(skill_ids) != int(record.get("skill_canonical_id_count") or 0):
                    consistency["skill_id_count_mismatch"] += 1
                if int(record.get("skill_token_count_raw") or 0) - len(tokens) != int(record.get("skill_duplicate_token_count") or 0):
                    consistency["skill_duplicate_token_count_mismatch"] += 1
                skill_stats["canonical_skill_assignment_rows"] += len(skill_ids)
                skill_stats["rows_with_any_skill_tokens"] += int(bool(tokens))
                for skill_id in skill_ids:
                    unique_skill_ids.add(skill_id)
                for token in tokens:
                    normalized = source_reader.normalize_skill_label(str(token))
                    if not normalized:
                        continue
                    metadata = source_reader.resolve_skill_metadata(str(token), skill_alias_reference)
                    item = skill_alias_audit.setdefault(normalized, {
                        "labels": Counter(), "skill_id": metadata["skill_id"],
                        "category": metadata["category"], "match_policy": metadata["match_policy"],
                        "review_status": metadata["review_status"], "source_datasets": set(), "job_record_count": 0,
                        "curated_alias_match": "yes" if normalized in skill_alias_reference else "no",
                    })
                    item["labels"][str(token)] += 1
                    item["source_datasets"].add(source_dataset)
                    item["job_record_count"] += 1
            except (ValueError, TypeError):
                consistency["skill_json_parse_failure"] += 1
            source_updated = record.get("source_updated_at_iso", "")
            posted = record.get("posted_at_iso", "")
            if not posted and source_updated:
                consistency_checked["updated_not_promoted"] += 1
                if "updated_not_used_as_posting_date" not in (record.get("date_quality_flags", "") or ""):
                    consistency["updated_not_promoted_flag_missing"] += 1
            if posted and cleaner.parse_source_datetime(posted) is None:
                consistency["posted_iso_unparseable"] += 1
            if source_updated and cleaner.parse_source_datetime(source_updated) is None:
                consistency["updated_iso_unparseable"] += 1
            if record.get("source_collected_at_iso") and cleaner.parse_source_datetime(record["source_collected_at_iso"]) is None:
                consistency["collection_iso_unparseable"] += 1
            # Salary range and three-currency cross-rate consistency.
            usd = _to_float(record.get("salary_annual_salary_usd"))
            egp = _to_float(record.get("salary_annual_salary_egp"))
            sar = _to_float(record.get("salary_annual_salary_sar"))
            if usd is not None and egp is not None:
                consistency_checked["salary_cross_rates"] += 1
                if not math.isclose(egp, usd * float(target_rates["EGP"]), rel_tol=1e-7, abs_tol=0.02):
                    consistency["annual_usd_egp_cross_rate_mismatch"] += 1
            if usd is not None and sar is not None:
                if not math.isclose(sar, usd * float(target_rates["SAR"]), rel_tol=1e-7, abs_tol=0.02):
                    consistency["annual_usd_sar_cross_rate_mismatch"] += 1
            for suffix in ("usd", "egp", "sar"):
                low = _to_float(record.get(f"salary_annual_min_{suffix}"))
                middle = _to_float(record.get(f"salary_annual_salary_{suffix}"))
                high = _to_float(record.get(f"salary_annual_max_{suffix}"))
                if middle is not None and low is not None and high is not None:
                    consistency_checked[f"salary_range_{suffix}"] += 1
                    if low > middle + 1e-7 or middle > high + 1e-7:
                        consistency[f"annual_salary_range_order_{suffix}_invalid"] += 1
            # Status should agree with the original raw classification and whether a model was applied.
            source_type = record.get("salary_source_value_type", "")
            final_type = record.get("salary_value_type", "")
            status = record.get("salary_estimation_status", "")
            consistency_checked["salary_status_relations"] += 1
            if source_type == "missing" and final_type == "estimated_synthetic" and status != "Estimated":
                consistency["synthetic_salary_status_mismatch"] += 1
            if source_type == "actual_reported" and status != "Actual":
                consistency["actual_salary_status_mismatch"] += 1
            if source_type in {"not_disclosed", "unparseable_or_no_numeric_amount"} and final_type == "estimated_synthetic":
                consistency["withheld_or_unparseable_salary_unexpectedly_imputed"] += 1
            if final_type == "estimated_synthetic" and status == "Estimated":
                consistency_checked["synthetic_salary_provenance"] += 1
                if not record.get("salary_estimation_method", "").startswith("synthetic_") or not record.get("salary_estimation_source", "").startswith("synthetic"):
                    consistency["synthetic_salary_provenance_missing"] += 1
            if record.get("exact_duplicate_within_source") == "yes":
                consistency_checked["exact_duplicates_retained"] += 1
            # Actual annual salary statistics include every valid converted, positive actual point;
            # review flags affect interpretation but do not delete these values.
            if source_type == "actual_reported" and usd is not None and usd > 0:
                family = record.get("role_family", "other_technology")
                country = record.get("country_standardized", "") or "__MISSING_COUNTRY__"
                seniority = record.get("seniority_band", "unspecified")
                actual_salary_groups[(country, family, seniority)].append(usd)
            if status == "Estimated":
                key = (record.get("salary_estimation_method", ""), record.get("country_standardized", ""), record.get("role_family", ""), record.get("seniority_band", ""))
                estimates_by_group[key]["estimated_records"] += 1

    skill_stats["unique_canonical_skill_ids_observed"] = len(unique_skill_ids)
    skill_alias_rows = []
    for normalized, item in sorted(skill_alias_audit.items(), key=lambda pair: (-pair[1]["job_record_count"], pair[0])):
        display_label = sorted(item["labels"], key=lambda label: (-item["labels"][label], label.casefold()))[0]
        skill_alias_rows.append({
            "alias_normalized": normalized,
            "observed_label": display_label,
            "skill_id": item["skill_id"],
            "skill_category": item["category"],
            "match_policy": item["match_policy"],
            "review_status": item["review_status"],
            "curated_alias_match": item["curated_alias_match"],
            "job_record_count": item["job_record_count"],
            "source_datasets": ";".join(sorted(item["source_datasets"])),
        })
    skill_alias_path = report_directory / "skill_alias_audit.csv"
    _write_plain_csv(skill_alias_path, ["alias_normalized", "observed_label", "skill_id", "skill_category", "match_policy", "review_status", "curated_alias_match", "job_record_count", "source_datasets"], skill_alias_rows)

    column_coverage_rows: list[dict[str, Any]] = []
    for source_file, source_meta in raw_summary["files"].items():
        source_rows = int(output_row_counts.get(source_file, 0))
        if not source_rows:
            continue
        source_dataset = next((spec["dataset"] for spec in cleaner.JOB_SOURCE_SPECS if spec["file"] == source_file), "reference_only")
        for field_name in all_fields:
            present = output_by_file[source_file][field_name]
            missing = max(0, source_rows - present)
            column_coverage_rows.append({
                "source_file": source_file,
                "source_dataset": source_dataset,
                "column_name": field_name,
                "rows": source_rows,
                "present_count": present,
                "missing_count": missing,
                "missing_percent": round(100.0 * missing / source_rows, 4) if source_rows else "",
            })
    cleaned_coverage_path = report_directory / "cleaned_column_coverage.csv"
    _write_plain_csv(cleaned_coverage_path, ["source_file", "source_dataset", "column_name", "rows", "present_count", "missing_count", "missing_percent"], column_coverage_rows)

    for field_name in all_fields:
        present = int(output_counts[field_name])
        missing = typed_rows - present
        expected = _expected_output_type(field_name)
        observed = type_observed[field_name]
        output_type_rows.append({
            "column_name": field_name,
            "expected_logical_type": expected,
            "nonmissing_values": present,
            "missing_values": missing,
            "missing_percent": round(100.0 * missing / typed_rows, 4) if typed_rows else "",
            "observed_value_shapes": json.dumps(dict(sorted(observed.items())), ensure_ascii=False, sort_keys=True),
            "invalid_type_values": type_invalid[field_name],
            "status": "passed" if type_invalid[field_name] == 0 else "review_required",
        })
    output_type_path = report_directory / "cleaned_column_type_audit.csv"
    _write_plain_csv(output_type_path, ["column_name", "expected_logical_type", "nonmissing_values", "missing_values", "missing_percent", "observed_value_shapes", "invalid_type_values", "status"], output_type_rows)

    # Date summaries for cleaned publication/update/collection columns are distinct.
    with gzip.open(dataset_path, "rt", encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            source_file = record.get("source_file", "")
            for field_name, date_class in (
                ("posted_at_iso", "publication_date"),
                ("source_updated_at_iso", "update_date"),
                ("source_collected_at_iso", "collection_date"),
            ):
                key = (source_file, field_name)
                detail = date_output_details.setdefault(key, {
                    "stage": "cleaned_output", "source_file": source_file, "field_name": field_name,
                    "date_class": date_class, "present": 0, "missing": 0, "parseable": 0,
                    "unparseable": 0, "before_2000": 0, "after_audit_date": 0, "earliest": "", "latest": "",
                })
                value = record.get(field_name, "")
                if _is_missing(value):
                    detail["missing"] += 1
                else:
                    detail["present"] += 1
                    parsed = cleaner.parse_source_datetime(value)
                    if parsed is None:
                        detail["unparseable"] += 1
                    else:
                        detail["parseable"] += 1
                        iso = cleaner.date_to_iso(parsed)
                        detail["earliest"] = min(detail["earliest"], iso) if detail["earliest"] else iso
                        detail["latest"] = max(detail["latest"], iso) if detail["latest"] else iso
                        detail["before_2000"] += int(parsed.date() < dt.date(2000, 1, 1))
                        detail["after_audit_date"] += int(parsed.date() > as_of_date)
    all_date_rows = raw_dates + [
        {**row, "missing_percent": round(100.0 * row["missing"] / (row["present"] + row["missing"]), 4) if row["present"] + row["missing"] else ""}
        for row in date_output_details.values()
    ]
    date_path = report_directory / "date_quality_audit.csv"
    _write_plain_csv(date_path, ["stage", "source_file", "field_name", "date_class", "present", "missing", "parseable", "unparseable", "before_2000", "after_audit_date", "earliest", "latest", "missing_percent"], all_date_rows)

    # Country spelling/alias and role-family crosswalks are diagnostic/derived only.
    country_rows = [
        {"country_raw": raw, "country_standardized": standard, "record_count": count, "changed_in_derived_column": "yes" if raw != standard else "no"}
        for (raw, standard), count in sorted(country_pairs.items(), key=lambda item: (-item[1], item[0][0].casefold(), item[0][1].casefold()))
    ]
    country_path = report_directory / "country_standardization_audit.csv"
    _write_plain_csv(country_path, ["country_raw", "country_standardized", "record_count", "changed_in_derived_column"], country_rows)
    family_rows = [{"source_dataset": source, "role_family": family, "record_count": count} for (source, family), count in sorted(role_family_counts.items())]
    family_path = report_directory / "role_family_profile.csv"
    _write_plain_csv(family_path, ["source_dataset", "role_family", "record_count"], family_rows)

    annual_actual_rows: list[dict[str, Any]] = []
    for (country, family, seniority), values in sorted(actual_salary_groups.items()):
        ordered = sorted(values)
        q1, q3 = cleaner._quantile(ordered, .25), cleaner._quantile(ordered, .75)
        iqr = q3 - q1
        low_bound, high_bound = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        potential_outliers = sum(value < low_bound or value > high_bound for value in values) if len(values) >= 8 else 0
        annual_actual_rows.append({
            "country": country,
            "role_family": family,
            "seniority_band": seniority,
            "actual_record_count": len(values),
            "median_annual_salary_usd": _format_number(statistics.median(values)),
            "q1_annual_salary_usd": _format_number(q1),
            "q3_annual_salary_usd": _format_number(q3),
            "minimum_annual_salary_usd_including_review_values": _format_number(min(values)),
            "maximum_annual_salary_usd_including_review_values": _format_number(max(values)),
            "potential_iqr_outliers_review_only": potential_outliers,
            "outlier_policy": "Included in the summary; IQR only flags records for review and never deletes or excludes them.",
        })
    actual_stats_path = report_directory / "annual_salary_statistics_actual.csv"
    _write_plain_csv(actual_stats_path, ["country", "role_family", "seniority_band", "actual_record_count", "median_annual_salary_usd", "q1_annual_salary_usd", "q3_annual_salary_usd", "minimum_annual_salary_usd_including_review_values", "maximum_annual_salary_usd_including_review_values", "potential_iqr_outliers_review_only", "outlier_policy"], annual_actual_rows)

    estimate_rows: list[dict[str, Any]] = []
    for key, counts in sorted(estimates_by_group.items()):
        method, country, family, seniority = key
        estimate_rows.append({
            "salary_estimation_method": method,
            "country_or_scope": country or "__MISSING_OR_NON_COUNTRY_SCOPE__",
            "role_family": family,
            "seniority_band": seniority,
            **counts,
            "model_reference_basis": "synthetic estimates use medians of source-reported actual salary records only; reference counts and fallback tier are stored per job record",
        })
    estimate_summary_path = report_directory / "salary_estimate_summary.csv"
    estimate_fields = ["salary_estimation_method", "country_or_scope", "role_family", "seniority_band", "estimated_records", "salary_annual_salary_usd_count", "salary_annual_salary_egp_count", "salary_annual_salary_sar_count", "model_reference_basis"]
    _write_plain_csv(estimate_summary_path, estimate_fields, estimate_rows)

    fx_rows: list[dict[str, Any]] = []
    for code, detail in sorted(fx_policy["currency_rate_details"].items()):
        rate_usd = float(fx_policy["fx_rates_to_reporting_currency"][code])
        fx_rows.append({
            "source_currency": code,
            "usd_per_source_currency_unit": _format_number(rate_usd),
            "egp_per_source_currency_unit": _format_number(rate_usd * float(target_rates["EGP"])),
            "sar_per_source_currency_unit": _format_number(rate_usd * float(target_rates["SAR"])),
            "fx_rate_date": fx_policy["fx_rate_date"],
            "rate_reference": detail.get("reference", ""),
            "source_url": detail.get("source_url", ""),
            "source_note": detail.get("source_note", ""),
        })
    fx_path = report_directory / "salary_fx_rates_used.csv"
    _write_plain_csv(fx_path, ["source_currency", "usd_per_source_currency_unit", "egp_per_source_currency_unit", "sar_per_source_currency_unit", "fx_rate_date", "rate_reference", "source_url", "source_note"], fx_rows)

    # Row-level change log is compactly gzipped. The source_row_json remains the immutable before value.
    duplicate_report = _duplicate_review_audit(dataset_path, report_directory)
    consistency_rows = []
    check_descriptions = {
        "record_id_uniqueness": "Record IDs are unique; no output row is lost or duplicated by the transform.",
        "row_retention": "Input/output row totals match and zero rows were dropped.",
        "field_type_validation": "Every cleaned output column is checked against its declared logical type.",
        "salary_cross_rates": "USD to EGP/SAR annual salary conversions match the frozen date-specific cross rates.",
        "salary_ranges": "For every annual salary with a range, minimum <= point estimate <= maximum.",
        "skill_json_counts": "Skill JSON arrays agree with their recorded token/ID counts.",
        "updated_not_promoted": "An update timestamp is not silently promoted to a posting timestamp.",
        "synthetic_salary_provenance": "Every synthetic estimate has an explicit synthetic method, source note and status.",
        "withheld_salary_protection": "Not-disclosed and unparseable values are not filled by the imputation model.",
        "database_reconciliation": "Project SQLite job and job-skill counts agree with the cleaned source rows / skill assignments.",
    }
    checks = {
        "record_id_uniqueness": (typed_rows, duplicate_record_ids),
        "row_retention": (typed_rows, 0 if typed_rows == logical_counts["rows_before"] else abs(typed_rows - logical_counts["rows_before"])),
        "field_type_validation": (len(all_fields), sum(type_invalid.values())),
        "salary_cross_rates": (consistency_checked["salary_cross_rates"], consistency["annual_usd_egp_cross_rate_mismatch"] + consistency["annual_usd_sar_cross_rate_mismatch"]),
        "salary_ranges": (sum(consistency_checked[f"salary_range_{code}"] for code in ("usd", "egp", "sar")), sum(value for key, value in consistency.items() if key.startswith("annual_salary_range_order_"))),
        "skill_json_counts": (consistency_checked["skill_json_counts"], consistency["skill_json_count_mismatch"] + consistency["skill_id_count_mismatch"] + consistency["skill_duplicate_token_count_mismatch"] + consistency["skill_json_parse_failure"]),
        "updated_not_promoted": (consistency_checked["updated_not_promoted"], consistency["updated_not_promoted_flag_missing"]),
        "synthetic_salary_provenance": (consistency_checked["synthetic_salary_provenance"], consistency["synthetic_salary_provenance_missing"]),
        "withheld_salary_protection": (consistency_checked["salary_status_relations"], consistency["withheld_or_unparseable_salary_unexpectedly_imputed"]),
        "database_reconciliation": (int((database_validation or {}).get("jobs_match", False)), 0 if (database_validation or {}).get("status") == "passed" else 1),
    }
    database_status = (database_validation or {}).get("status", "not_checked")
    if database_status == "not_checked":
        checks["database_reconciliation"] = (0, 0)
    consistency_results = {}
    for name, (checked, violations) in checks.items():
        not_checked = name == "database_reconciliation" and database_status == "not_checked"
        status = "not_checked" if not_checked else ("passed" if violations == 0 else "failed")
        consistency_result = {
            "records_or_columns_checked": checked,
            "violations": None if not_checked else violations,
            "status": status,
        }
        consistency_results[name] = consistency_result
        consistency_rows.append({
            "check_name": name,
            "records_or_columns_checked": checked,
            "violations": "" if not_checked else violations,
            "status": status,
            "description": check_descriptions[name],
        })
    consistency_path = report_directory / "field_consistency_checks.csv"
    _write_plain_csv(consistency_path, ["check_name", "records_or_columns_checked", "violations", "status", "description"], consistency_rows)

    missing_impact_rows: list[dict[str, Any]] = []
    coverage_rows = []
    with logical_coverage_path.open("r", encoding="utf-8", newline="") as handle:
        coverage_rows = list(csv.DictReader(handle))
    impacts = {
        "title": "High: role matching and family salary estimate degrade; no title is invented.",
        "company": "Medium: cross-source duplicate resolution is less reliable.",
        "country": "High: local salary context and location segmentation are unavailable.",
        "description": "Medium: semantic skill validation and role detail are limited.",
        "source_url": "Medium: the listing cannot be independently reviewed from a URL.",
        "skills": "High for skill matching: no skill assignment is invented; blank stays blank.",
        "salary_original_text": "High for observed salary analysis; synthetic annual estimate is separate and explicitly labeled.",
        "salary_any_numeric_source": "High for observed pay analysis; synthetic estimate does not replace source pay.",
        "annualized_salary_usd": "High for comparable annual-pay analysis; conversion remains blank when source currency or pay period is unresolved.",
        "publication_date": "Medium: freshness/historical analysis cannot use an inferred date.",
        "source_update_date": "Medium: update time is not treated as publication or collection date.",
        "source_collection_date": "Low/unknown: collection time is only reported when an explicit source column is present; no external timestamp is inferred.",
    }
    for row in coverage_rows:
        logical = row["logical_field"]
        missing_impact_rows.append({
            "source_file": row["source_file"],
            "logical_field": logical,
            "rows": row["rows_before"],
            "missing_original_count": row["before_missing"],
            "missing_original_percent": row["before_missing_percent"],
            "missing_cleaned_count": row["after_missing"],
            "missing_cleaned_percent": row["after_missing_percent"],
            "impact_if_missing": impacts[logical],
        })
    missing_path = report_directory / "missingness_impact.csv"
    _write_plain_csv(missing_path, ["source_file", "logical_field", "rows", "missing_original_count", "missing_original_percent", "missing_cleaned_count", "missing_cleaned_percent", "impact_if_missing"], missing_impact_rows)

    source_type_invalid = sum(int(row.get("invalid_type_values", 0)) for row in output_type_rows)
    salary_counter = Counter()
    for row in output_type_rows:
        if row["column_name"] in {"salary_original", "salary_annual_salary_usd", "salary_annual_salary_egp", "salary_annual_salary_sar"}:
            salary_counter[row["column_name"] + "_missing"] = int(row["missing_values"])
    before_path = report_directory / "data_quality_before.json"
    before = json.loads(before_path.read_text(encoding="utf-8")) if before_path.is_file() else {}
    before["full_source_audit"] = raw_summary
    before["raw_source_column_count"] = len(raw_types)
    before["raw_source_column_coverage_path"] = _workspace_path_label(raw_column_path)
    before["raw_source_type_audit_path"] = _workspace_path_label(raw_type_path)
    before["date_audit_path"] = _workspace_path_label(date_path)
    before["note"] = "Before-cleaning field availability was measured on raw input rows; all source values are read as strings, with logical value shapes recorded separately."
    _write_json(before_path, before)

    after = {
        "metadata": {
            "audit_date": as_of_date.isoformat(),
            "source_ref": json.loads((report_directory / "cleaning_summary.json").read_text(encoding="utf-8")).get("source_ref", ""),
            "cleaned_dataset_path": _workspace_path_label(dataset_path),
            "salary_reporting_currency_base": "USD",
            "target_currencies": ["USD", "EGP", "SAR"],
            "note": "All original rows and raw source JSON are retained. Synthetic salary fields are separate from source salary fields.",
        },
        "rows": {"before": logical_counts["rows_before"], "after": typed_rows, "dropped": logical_counts["rows_before"] - typed_rows},
        "output_column_count": len(all_fields),
        "field_coverage": {
            field: {
                "present": int(output_counts[field]),
                "missing": typed_rows - int(output_counts[field]),
                "missing_rate": round((typed_rows - int(output_counts[field])) / typed_rows, 6) if typed_rows else None,
            }
            for field in all_fields
        },
        "field_coverage_comparison_path": _workspace_path_label(logical_coverage_path),
        "full_column_coverage_path": _workspace_path_label(cleaned_coverage_path),
        "column_type_audit_path": _workspace_path_label(output_type_path),
        "raw_source_column_coverage_path": _workspace_path_label(raw_column_path),
        "date_quality_audit_path": _workspace_path_label(date_path),
        "salary": {
            "source_value_type_counts": dict(salary_value_type_counts),
            "estimation_status_counts": dict(salary_status_counts),
            "salary_estimation_method_counts": dict(salary_estimate_method_counts),
            "source_currency_counts": dict(salary_currency_counts),
            "annual_salary_available_by_currency": dict(annual_salary_available_counts),
            "salary_original_missing_after_estimation": salary_counter.get("salary_original_missing", 0),
            "annual_salary_usd_missing": salary_counter.get("salary_annual_salary_usd_missing", 0),
            "annual_salary_egp_missing": salary_counter.get("salary_annual_salary_egp_missing", 0),
            "annual_salary_sar_missing": salary_counter.get("salary_annual_salary_sar_missing", 0),
        },
        "types": {
            "output_columns_checked": len(all_fields),
            "output_invalid_type_values": source_type_invalid,
            "source_columns_checked": len(raw_types),
            "output_type_audit_status": "passed" if source_type_invalid == 0 else "review_required",
        },
        "dates": {
            "collection_date_source_fields_found": raw_summary["collection_date_source_columns"],
            "collection_date_records_present": sum(row["present"] for row in date_output_details.values() if row["date_class"] == "collection_date"),
            "policy": "Publication, source-update, and source-collection columns are separate. 'updated' is never promoted to publication; no collection date is inferred from file/Drive timestamps.",
        },
        "duplicates": duplicate_report,
        "skills": {
            **dict(skill_stats),
            "unique_observed_skill_aliases": len(skill_alias_rows),
            "curated_alias_token_keys": sum(row["curated_alias_match"] == "yes" for row in skill_alias_rows),
            "unreviewed_exact_only_token_keys": sum(row["curated_alias_match"] == "no" for row in skill_alias_rows),
            "alias_audit_path": _workspace_path_label(skill_alias_path),
        },
        "role_family_counts": {f"{source}|{family}": count for (source, family), count in role_family_counts.items()},
        "country_standardization_pair_count": len(country_pairs),
        "field_consistency": dict(consistency),
        "database_validation": database_validation or {"status": "not_checked"},
        "source_integrity": json.loads((report_directory / "cleaning_summary.json").read_text(encoding="utf-8")).get("source_integrity", {}),
    }
    after_path = report_directory / "data_quality_after.json"
    _write_json(after_path, after)

    model_report = {
        "fx_policy_path": fx_policy.get("policy_path", _workspace_path_label(DEFAULT_FX_POLICY)),
        "fx_policy": fx_policy,
        "benchmark_model": {
            **benchmark_report,
            "group_count": len(models),
            "minimum_reference_counts": {
                "exact_country_title": 5, "country_family_seniority": 8, "country_family": 12,
                "global_family_seniority": 12, "global_family": 15, "global_technology": 25,
            },
            "fallback_order": ["exact_country_title", "country_family_seniority", "country_family", "global_family_seniority", "global_family", "global_technology"],
            "reference_salary_policy": "Only source-reported actual rows with salary_statistics_eligible=yes, explicit currency/pay period, and valid annual USD values train the model. Legacy/synthetic estimates and scale-review rows are excluded; IQR outliers within the eligible reference pool are retained and median is robust to them.",
        },
        "deliverables": {
            "raw_source_column_coverage": _workspace_path_label(raw_column_path),
            "raw_source_type_audit": _workspace_path_label(raw_type_path),
            "cleaned_column_coverage": _workspace_path_label(cleaned_coverage_path),
            "cleaned_column_type_audit": _workspace_path_label(output_type_path),
            "field_coverage_comparison": _workspace_path_label(logical_coverage_path),
            "date_quality_audit": _workspace_path_label(date_path),
            "missingness_impact": _workspace_path_label(missing_path),
            "country_standardization_audit": _workspace_path_label(country_path),
            "role_family_profile": _workspace_path_label(family_path),
            "annual_salary_statistics_actual": _workspace_path_label(actual_stats_path),
            "salary_estimate_summary": _workspace_path_label(estimate_summary_path),
            "salary_fx_rates_used": _workspace_path_label(fx_path),
            "skill_alias_audit": _workspace_path_label(skill_alias_path),
            "duplicate_review_candidates": _workspace_path_label(Path(duplicate_report["candidate_file"])),
            "field_consistency_checks": _workspace_path_label(consistency_path),
        },
    }
    _write_json(report_directory / "salary_model_and_fx_policy.json", model_report)
    return {
        "rows": typed_rows,
        "columns": len(all_fields),
        "type_invalid_values": source_type_invalid,
        "source_column_count": len(raw_types),
        "output_type_audit_path": str(output_type_path),
        "raw_summary": raw_summary,
        "logical_counts": logical_counts,
        "salary_status_counts": dict(salary_status_counts),
        "salary_value_type_counts": dict(salary_value_type_counts),
        "salary_method_counts": dict(salary_estimate_method_counts),
        "salary_currency_counts": dict(salary_currency_counts),
        "annual_salary_available_counts": dict(annual_salary_available_counts),
        "salary_missing": salary_counter,
        "skills": {
            **dict(skill_stats),
            "unique_observed_skill_aliases": len(skill_alias_rows),
            "curated_alias_token_keys": sum(row["curated_alias_match"] == "yes" for row in skill_alias_rows),
            "unreviewed_exact_only_token_keys": sum(row["curated_alias_match"] == "no" for row in skill_alias_rows),
            "alias_audit_path": _workspace_path_label(skill_alias_path),
        },
        "duplicate_report": duplicate_report,
        "consistency": dict(consistency),
        "consistency_checks": consistency_results,
        "database_validation": database_validation or {"status": "not_checked"},
        "annual_salary_statistics_path": str(actual_stats_path),
        "estimate_summary_path": str(estimate_summary_path),
        "skill_alias_audit_path": str(skill_alias_path),
        "fx_path": str(fx_path),
        "consistency_path": str(consistency_path),
        "missingness_path": str(missing_path),
        "logical_coverage_path": str(logical_coverage_path),
        "date_path": str(date_path),
        "country_path": str(country_path),
        "family_path": str(family_path),
        "cleaned_coverage_path": str(cleaned_coverage_path),
        "raw_coverage_path": str(raw_column_path),
        "raw_type_path": str(raw_type_path),
    }


def _notebook_cell(cell_type: str, source: str) -> dict[str, Any]:
    cell: dict[str, Any] = {"cell_type": cell_type, "metadata": {}, "source": source.splitlines(keepends=True)}
    if cell_type == "code":
        cell.update({"execution_count": None, "outputs": []})
    return cell


def _write_notebook(path: Path, summary: Mapping[str, Any], audit: Mapping[str, Any]) -> None:
    salary = summary.get("salary", {})
    salary_policy = summary.get("salary_policy", {})
    benchmark_report = salary_policy.get("benchmark_training", {})
    audit_date = str(summary.get("audit_date", "2026-10-28"))
    source_ref = str(summary.get("source_ref", "unspecified")).replace("'", "\\'")
    fx_path = str(salary_policy.get("fx_policy_path", "data/reference/fx_rates_2026-10-28.json"))
    cells = [
        _notebook_cell("markdown", f"""# دفتر تنظيف وتدقيق جودة بيانات الوظائف التقنية — التشغيل الكامل

- **تاريخ التدقيق:** {audit_date}
- **مرجع المصادر:** `{summary.get('source_ref', '')}`
- **الصفوف قبل/بعد:** {summary.get('input_rows', 0):,} / {summary.get('output_rows', 0):,}
- **الصفوف المحذوفة:** {summary.get('rows_dropped', 0):,}

هذا الدفتر يوثق التنظيف على مصادر التشغيل المسجل. ملفات المصدر للقراءة فقط؛ كل صف خام محفوظ في `source_row_json`. لا تُدمج الإعلانات أو المهارات دلاليًا ولا تُحذف outliers. ملف الوظائف المنظف يبقى في Drive ولا يُضم إلى Git؛ عند استعادته محليًا إلى `data/processed/` يستطيع الدفتر فحص عدد صفوفه تدفقيًا.
"""),
        _notebook_cell("markdown", """## 1. النطاق ومصدر البيانات

تُسجل المصادر المختارة ونسخ base المستخدمة لمقارنة إثراء المهارات في `source_manifest.csv`. لا تُضاف صفوف نسخ base مرة أخرى. أي اختلاف في timestamp خارجي عن تاريخ التدقيق يُذكر كقيد provenance، ولا يُعامل تاريخًا للنشر أو الجمع.

## 2. سياسة التغييرات

الأصل محفوظ؛ التنظيف والتوحيد في أعمدة مشتقة. التطبيع النصي لا يوحد معاني العناوين أو البلدان تقريبيًا. التكرارات exact/near كلها مرشحة للمراجعة فقط ولا تُحذف. إعلانات `updated` منفصلة عن `posted`، ولا تُستنتج تواريخ الجمع من timestamps خارجية.
"""),
        _notebook_cell("markdown", f"""## 3. الرواتب: التحويل والتقدير

- `salary_original` / `salary_raw` تحفظ القيمة المصدرية كما هي؛ أي قيمة مضافة مستقلة في أعمدة سنوية مشتقة.
- عوامل السنونة الصريحة: شهر ×{salary_policy.get('annualization_factors', {}).get('MONTH', 12)}, أسبوع ×{salary_policy.get('annualization_factors', {}).get('WEEK', 52)}, يوم عمل ×{salary_policy.get('annualization_factors', {}).get('DAY', 260)}, ساعة ×{salary_policy.get('annualization_factors', {}).get('HOUR', 2080)}. العوامل افتراضات موثقة وليست حقائق من المصدر.
- القيمة الموحدة الأساسية USD؛ تُشتق EGP وSAR باستخدام سياسة الصرف المؤرخة. لا يوجد تعديل تضخم أو PPP.
- مرجع التقدير يستخدم فقط `actual_reported` مع `salary_statistics_eligible=yes`، وعملة وفترة صريحتين وقيمة سنوية USD موجبة صالحة؛ استُخدمت {benchmark_report.get('benchmark_actual_record_count', 0):,} سجلات ضمن {benchmark_report.get('benchmark_group_count', 0):,} مجموعات.
- التقديرات المضافة في هذا التشغيل: {salary.get('estimates_added_by_this_run', 0):,}. كل قيمة Synthetic موسومة Estimated مع المنهج والثقة وعدد المراجع؛ نطاق Q1–Q3 مرجع Synthetic داخلي وليس نطاق راتب معلن.
- `Not disclosed` والنص غير القابل للتحليل والعملة/الفترة الغامضة لا تُخمن لها قيم. القيم الشاذة محفوظة وموسومة فقط.
"""),
        _notebook_cell("code", """from pathlib import Path
import csv
import gzip
import json

def find_project_root(start=None):
    current = Path(start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / 'scripts' / 'data_cleaning' / 'finalize_full_cleaning_audit.py').is_file():
            return candidate
    raise FileNotFoundError('Repository root not found')

PROJECT_ROOT = find_project_root()
REPORT_DIR = PROJECT_ROOT / 'analysis' / 'reports' / 'data_cleaning'
DATASET = PROJECT_ROOT / 'data' / 'processed' / 'jobs_cleaned_audited.csv.gz'
SUMMARY = json.loads((REPORT_DIR / 'cleaning_summary.json').read_text(encoding='utf-8'))
BEFORE = json.loads((REPORT_DIR / 'data_quality_before.json').read_text(encoding='utf-8'))
AFTER = json.loads((REPORT_DIR / 'data_quality_after.json').read_text(encoding='utf-8'))
print('scope:', SUMMARY['scope'])
print('rows before / after / dropped:', SUMMARY['input_rows'], SUMMARY['output_rows'], SUMMARY['rows_dropped'])

if DATASET.is_file():
    print('dataset bytes:', DATASET.stat().st_size)
    streamed_rows = 0
    missing_core_fields = 0
    with gzip.open(DATASET, 'rt', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        required = {'record_id', 'source_row_json'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f'Missing required audit columns: {sorted(required - set(reader.fieldnames or []))}')
        for row in reader:
            streamed_rows += 1
            if not row.get('record_id') or not row.get('source_row_json'):
                missing_core_fields += 1
    assert streamed_rows == int(SUMMARY['output_rows']), (streamed_rows, SUMMARY['output_rows'])
    assert missing_core_fields == 0, missing_core_fields
    print('stream-validated rows:', streamed_rows, '| missing core fields:', missing_core_fields)
else:
    print('Cleaned dataset is not in this Git checkout. Restore jobs_cleaned_audited.csv.gz from Drive to data/processed/ to run the streaming row-count check.')"""),
        _notebook_cell("markdown", "## 4. التغطية والحقول والأنواع\n\n`raw_source_column_coverage.csv` و`cleaned_column_coverage.csv` و`field_coverage_comparison.csv` تلخص المفقود حسب المصدر/الحقل. `cleaned_column_type_audit.csv` يفحص أعمدة الناتج؛ وتُعرض خلاصاتها هنا، دون تضمين الداتا المنظفة نفسها في Git."),
        _notebook_cell("code", """def read_csv(path):
    with Path(path).open('r', encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))

missing = read_csv(REPORT_DIR / 'missingness_impact.csv')
print('Highest-impact fields with the most original missing values:')
for row in sorted(missing, key=lambda r: int(r['missing_original_count'] or 0), reverse=True)[:12]:
    print(row['source_file'], row['logical_field'], row['missing_original_count'], row['missing_original_percent'] + '%')
types = read_csv(REPORT_DIR / 'cleaned_column_type_audit.csv')
print('Output columns checked:', len(types), '| invalid typed values:', sum(int(r['invalid_type_values']) for r in types))"""),
        _notebook_cell("markdown", "## 5. التواريخ والتكرارات والمهارات\n\nيسجل التقرير النهائي حدود فحص تواريخ النشر والتحديث والجمع، والأعداد المجمعة للتكرارات والمرشحين. لا يثبت التشابه أن الإعلان مكرر، ولا تُحذف أو تُدمج أي صفوف. تُحفظ تفاصيل المراجعة الصفّية وجداول المهارات الكبيرة كمخرجات محلية مولّدة ولا تُضاف إلى Git."),
        _notebook_cell("code", """duplicate_review = SUMMARY.get('full_data_quality_audit', {}).get('duplicate_review', {})
for key in (
    'candidate_groups_total',
    'cross_source_exact_raw_row_groups',
    'cross_source_exact_url_groups',
    'cross_source_exact_listing_signature_groups',
    'cross_source_near_duplicate_pairs',
    'large_near_duplicate_blocks_skipped_over_60_rows',
    'deleted_or_merged_rows',
):
    print(key, duplicate_review.get(key, 'not_available'))

checks = read_csv(REPORT_DIR / 'field_consistency_checks.csv')
for row in checks:
    print(row['check_name'], row['status'], 'violations=', row['violations'])"""),
        _notebook_cell("markdown", f"""## 6. الرواتب والتحليلات المُعادة

الراتب الأصلي يبقى محفوظًا، وتُفصل القيم المصدرية الفعلية عن القيم السنوية المحولة وعن التقديرات الاصطناعية الموسومة. يُراجع المنهج والحدود في `analysis/reports/data_cleaning/final_data_quality_report.md`؛ أسعار الصرف والسنونة المؤرخة في `{fx_path}`. جداول الرواتب الصفّية والتفصيلية ليست ضمن Git.

## 7. التشغيل وإعادة الإنتاج

```bash
python scripts/data_cleaning/build_cleaning_audit.py \
  --raw-data-directory /path/to/restored/data/raw \
  --dataset-output data/processed/jobs_cleaned_audited.csv.gz \
  --report-directory analysis/reports/data_cleaning \
  --source-ref '{source_ref}' \
  --as-of-date {audit_date} --require-all-sources
python scripts/data_cleaning/finalize_full_cleaning_audit.py \
  --raw-data-directory /path/to/restored/data/raw \
  --dataset data/processed/jobs_cleaned_audited.csv.gz \
  --report-directory analysis/reports/data_cleaning \
  --source-ref '{source_ref}' \
  --as-of-date {audit_date} \
  --fx-policy-file {fx_path}
```

يجب أن يحتوي المجلد على كل المصادر المحددة ونسخ base اللازمة. لا تُوصف مجموعة جزئية بأنها كاملة. بيانات المصدر والمنظفة موجودة في Drive وليستا جزءًا من نشر ملفات التنظيف على GitHub.
"""),
    ]
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

def _write_final_report(path: Path, summary: Mapping[str, Any], audit: Mapping[str, Any], fx_policy: Mapping[str, Any]) -> None:
    salary = summary.get("salary", {})
    duplicate = audit["duplicate_report"]
    database = audit.get("database_validation", {})
    status_counts = audit["salary_status_counts"]
    annual_counts = audit["annual_salary_available_counts"]
    source_counts = summary.get("file_reports", {})
    benchmark_report = summary.get("salary_policy", {}).get("benchmark_training", {})
    database_status = database.get("status", "not_checked")
    if database_status == "not_checked":
        database_detail_line = "- مطابقة قاعدة البيانات الخارجية: `not_checked`؛ قاعدة المشروع السابقة وحزمة Parquet غير متاحتين في checkout، ولم يُمرر `--database-validation-json`."
    else:
        database_detail_line = f"- مطابقة قاعدة البيانات الخارجية: `{database_status}`؛ قاعدة البيانات `{database.get('database_path', 'غير محددة')}`، jobs={database.get('database_job_rows', 0):,}، job-skill links={database.get('database_job_skill_rows', 0):,}."
    sqlite_round_trip = summary.get("sqlite_round_trip", {})
    sqlite_round_trip_line = (
        f"- فحص SQLite الداخلي لقراءة CSV وتجميع الرواتب: `{sqlite_round_trip.get('status', 'not_checked')}`؛ "
        f"{sqlite_round_trip.get('dataset_rows_read', 0):,} صفًا، {sqlite_round_trip.get('salary_groups_compared', 0):,} مجموعة راتب، "
        f"{sqlite_round_trip.get('mismatch_count', len(sqlite_round_trip.get('mismatches', []))):,} اختلافًا. هذا ليس مقارنة مع قاعدة المشروع المفقودة."
    )
    lines = [
        "# تقرير تدقيق جودة البيانات والتنظيف الكامل",
        "",
        f"- **تاريخ التدقيق:** {summary.get('audit_date', '')}",
        f"- **مرجع المصادر:** `{summary.get('source_ref', '')}`",
        f"- **النطاق:** `{summary.get('scope', '')}`",
        f"- **البيانات المنظفة:** `{summary.get('cleaned_dataset_path', '')}`",
        f"- **SHA-256 للبيانات المنظفة:** `{summary.get('cleaned_dataset_sha256', '')}`",
        "",
        "## النطاق واستعادة المصادر",
        "",
        f"شمل التشغيل **{summary.get('available_job_source_count', 0)} ملفات وظائف و{summary.get('input_rows', 0):,} صفًا**، إضافةً إلى ملفات base الثلاثة المستخدمة لمراجعة إثراء المهارات فقط. احتُفظ بكل صف: **{summary.get('rows_dropped', 0):,} صف محذوف**. المصادر الخام لم تُعدّل.",
        "",
        "ملاحظة provenance: ملف International استُعيد من ZIP في Google Drive. تاريخ تعديل Drive المسجل `2026-10-31` لاحق لتاريخ التدقيق `2026-10-28`؛ سُجل الفرق ولم يُعامل تاريخ الملف كتاريخ نشر أو جمع.",
        "",
        "### جرد المصادر المختارة",
        "",
        "| المصدر | الصفوف | SHA-256 (بادئة) | exact duplicates محفوظة |",
        "|---|---:|---|---:|",
    ]
    for filename, detail in source_counts.items():
        if int(detail.get("rows", 0)) == 0:
            continue
        lines.append(f"| `{filename}` | {int(detail.get('rows', 0)):,} | `{str(detail.get('source_sha256', ''))[:16]}` | {int(detail.get('exact_duplicate_occurrences_retained', 0)):,} |")
    lines.extend([
        "",
        "## التغطية والمفقود قبل/بعد",
        "",
        "التغطية الكاملة لكل عمود خام موجودة في `raw_source_column_coverage.csv`, ولكل عمود نهائي وفي كل مصدر في `cleaned_column_coverage.csv`. الحقول المشتركة ملخصة أدناه؛ المفقود لا يُستبدل إلا في الأعمدة المشتقة المسموح بها، والراتب الأصلي يبقى كما ورد.",
        "",
        "| الحقل المنطقي | المصدر | مفقود قبل | النسبة قبل | مفقود بعد | النسبة بعد | أثر النقص |",
        "|---|---|---:|---:|---:|---:|---|",
    ])
    coverage_rows = []
    with (path.parent / "field_coverage_comparison.csv").open("r", encoding="utf-8", newline="") as handle:
        coverage_rows = list(csv.DictReader(handle))
    for row in coverage_rows:
        if row["logical_field"] in {"title", "country", "skills", "salary_original_text", "salary_any_numeric_source", "publication_date", "source_collection_date"}:
            lines.append(f"| {row['logical_field']} | `{row['source_file']}` | {int(row['before_missing']):,} | {row['before_missing_percent']}% | {int(row['after_missing']):,} | {row['after_missing_percent']}% | {row['high_impact_if_missing']} |")
    lines.extend([
        "",
        "- عدد أعمدة dataset النهائي: **{:,}**؛ جرى فحص نوع كل عمود، والأنواع المخالفة: **{}**.".format(audit["columns"], audit["type_invalid_values"]),
        f"- الحقول المنطقية قبل/بعد: **{audit['logical_counts']['rows_before']:,} / {audit['rows']:,}**؛ الفارق **{audit['logical_counts']['rows_before'] - audit['rows']:,}**.",
        "- تقرير الأنواع الخام يتعامل مع CSV/XLSX كنص المصدر ويحصر الأشكال الرقمية/المنطقية/التاريخية المكتشفة؛ التحويل المنطقي محصور في الأعمدة المشتقة.",
        "",
        "## مراجعة الأنواع والتواريخ والتوحيد",
        "",
        f"- أعمدة المصدر المفحوصة: **{audit['source_column_count']}** سجل عمود/مصدر؛ أعمدة النتيجة المفحوصة: **{audit['columns']}**.",
        f"- حقل وقت الجمع الصريح المكتشف: **{len(audit['raw_summary']['collection_date_source_columns'])}**. إذا لم يظهر حقل جمع، تبقى قيمة collection فارغة؛ لم تُستخدم تواريخ Drive أو modified كبديل.",
        "- `posted_at_iso` يقرأ حقول النشر فقط. `source_updated_at_iso` مستقل، ولا يتحول إلى نشر. `source_collected_at_iso` يقرأ أعمدة الجمع/السحب الصريحة فقط.",
        "- الدول: aliases صريحة فقط في `country_standardized`؛ النص الخام محفوظ. العنوان يبقى دلاليًا كما هو مع تطبيع المسافات و`title_key` غير حساس لحالة الأحرف فقط. لم يُدمج عنوانان متشابهان تلقائيًا.",
        "- المواقع والمدن والمناطق الخام محفوظة؛ أضيف `location_clean` لتطبيع المسافات و`location_key` للمقارنة النصية. تصنيفات العمل/نوع التوظيف و`role_family` أعمدة مشتقة مع الاحتفاظ بالقيم الخام.",
        "- نتائج النوع والتاريخ والتوحيد: `cleaned_column_type_audit.csv`, `raw_source_type_audit.csv`, `date_quality_audit.csv`, `country_standardization_audit.csv`, و`role_family_profile.csv`.",
        "",
        "## التكرارات والقيم الشاذة",
        "",
        f"- exact داخل المصدر محفوظ وموسوم: **{summary.get('exact_duplicate_occurrences_retained', 0):,}**.",
        f"- مرشحو التطابق عبر المصادر: raw-row **{duplicate['cross_source_exact_raw_row_groups']:,}**، URL **{duplicate['cross_source_exact_url_groups']:,}**، توقيع إعلان **{duplicate['cross_source_exact_listing_signature_groups']:,}**؛ near duplicate **{duplicate['cross_source_near_duplicate_pairs']:,}** زوجًا.",
        f"- لم يُحذف أو يُدمج أي مرشح. جرى تخطي **{duplicate['large_near_duplicate_blocks_skipped_over_60_rows']:,}** كتل متشابهة كبيرة (>60 صفًا) في المقارنة الثنائية المكلفة؛ لم تُحذف سجلاتها، وتُذكر حدود الفحص صراحة.",
        "- قيم الرواتب التي تخرج عن IQR أو الحدود الواسعة تبقى في الملف وتُوسم للمراجعة. جدول `annual_salary_statistics_actual.csv` يتضمن الحد الأدنى والأعلى مع العلامة، ولا يحذف أو يقص قيمة.",
        "- كل المرشحين للتكرار في `duplicate_review_candidates.csv`؛ العلامة ليست تأكيدًا أن الإعلانات تمثل الوظيفة نفسها.",
        "",
        "## توحيد الرواتب والتقدير الاصطناعي",
        "",
        "- `salary_raw` و`salary_candidate_raw` و`salary_original` و`source_row_json` تحفظ أصل الراتب. القيم المحولة/السنوية أعمدة منفصلة.",
        f"- العملة الأساسية: **USD**؛ القيم السنوية النظيرة متاحة في **USD وEGP وSAR**. اختيار USD كقاعدة قرار افتراضي موثق لأن المستخدم لم يحدد قاعدة وحيدة؛ تُعرض العملات الثلاث معًا.",
        "- معدلات التحويل مؤرخة **{}**؛ USD→EGP = **{}**، USD→SAR = **{}**. التحويل من العملات الأخرى إلى USD موثق لكل عملة في `salary_fx_rates_used.csv` و`data/reference/fx_rates_2026-10-28.json`. جميع الرواتب، حتى ذات تاريخ نشر أقدم، حُولت بسعر يوم التدقيق؛ لا يوجد تعديل تضخم أو PPP.".format(fx_policy['fx_rate_date'], fx_policy['target_currency_rates_from_usd']['EGP'], fx_policy['target_currency_rates_from_usd']['SAR']),
        f"- عوامل السنونة: الشهر ×{fx_policy['annualization_factors']['MONTH']}، الأسبوع ×{fx_policy['annualization_factors']['WEEK']}، يوم العمل ×{fx_policy['annualization_factors']['DAY']}، الساعة ×{fx_policy['annualization_factors']['HOUR']}؛ افتراض الساعة **40 × 52 = 2,080**. فترة غير معروفة لا تُسنون تخمينًا.",
        f"- أعداد الحالة النهائية: Actual **{status_counts.get('Actual', 0):,}**، Estimated **{status_counts.get('Estimated', 0):,}**، Unverified **{status_counts.get('Unverified', 0):,}**، Not disclosed **{status_counts.get('Not disclosed', 0):,}**، Unparseable **{status_counts.get('Unparseable', 0):,}**، Missing بلا تقدير **{status_counts.get('Missing', 0):,}**.",
        f"- قِيَم راتب مفقودة أصلًا ملئت بتقدير Synthetic وموسومة Estimated: **{salary.get('estimates_added_by_this_run', 0):,}**. المصدر يبقى فارغًا في `salary_original`؛ لا تُعرض التقديرات كرواتب معلنة أو كمصادر خارجية. المنهج وعدد مراجع كل سجل والثقة في أعمدته.",
        f"- راتب أصلي مفقود لكن لم يُقدّر لعدم وجود مرجع كافٍ: **{salary.get('missing_records_after_estimation', 0):,}**؛ القيم غير المفصح عنها لا تُقدّر، والنص غير القابل للتحليل لا يُستبدل.",
        f"- تغطية الراتب السنوي بعد التحويل: USD **{annual_counts.get('USD', 0):,}**، EGP **{annual_counts.get('EGP', 0):,}**، SAR **{annual_counts.get('SAR', 0):,}**.",
        f"- الرواتب الأصلية المفقودة قبل التقدير: **{salary.get('original_missing_records', 0):,}**؛ القيم synthetic لا تدخل في إحصاءات Actual أو تدريب مرجع التقدير.",
        f"- نموذج التقدير: وسيط من Actual المصدرية المؤهلة فقط، بتدرج بلد+عنوان، بلد+عائلة دور+خبرة، بلد+عائلة، عالمي+عائلة+خبرة، عالمي+عائلة، ثم عالمي. أهلية التدريب: `salary_value_type=actual_reported` و`salary_statistics_eligible=yes`، عملة وفترة معلنتان وقيمة سنوية USD موجبة صالحة؛ استُخدمت **{benchmark_report['benchmark_actual_record_count']:,}** سجلات في **{benchmark_report['benchmark_group_count']:,}** مجموعات. الأعداد حسب المصدر/العملة والسياسة في `salary_model_and_fx_policy.json`. قيم IQR المتطرفة تبقى ولا تُحذف، والوسيط مقاوم لها؛ Q1–Q3 للمجموعة المرجعية نطاق Synthetic مرجعي لا نطاق راتب معلن.",
        "- يظل `Actual` مبلغًا ظهر في ملف المصدر ولم يُتحقق حيًا من الإعلان. `Unverified` ليس راتبًا محققًا. التقديرات الموروثة تبقى `Estimated` لكن غير متحققة.",
        "",
        "### ملفات الرواتب",
        "",
        "- `salary_estimate_summary.csv` حسب البلد/العائلة/المنهج؛ `salary_fx_rates_used.csv` أسعار العملة؛ `annual_salary_statistics_actual.csv` إحصاءات الرواتب الفعلية المحولة سنويًا؛ `salary_statistics_actual.csv` الإحصاءات الأصلية حسب العملة والفترة.",
        "- `salary_review_candidates.csv` لحالات مراجعة العملة/الفترة/المصدر/النطاق. لا تُخلط الرواتب المعلنة بالتقديرات.",
        "",
        "## المهارات والحقول المرتبطة",
        "",
        f"- صفوف بها tokens مهارات: **{audit['skills'].get('rows_with_any_skill_tokens', 0):,}**؛ مجموع assignments canonical: **{audit['skills'].get('canonical_skill_assignment_rows', 0):,}**.",
        "- التكرار داخل قائمة المهارة يُزال فقط من القائمة المشتقة؛ `skills_raw` لا يتغير. alias mapping صريح/محافظ؛ المصطلحات غير المراجعة تبقى exact-only ولا تُستبدل بمرادفات.",
        "- الاختبارات تشمل تطابق عدد مهارات JSON مع العدّ، اتساق USD↔EGP/SAR، ترتيب حدود الراتب، عدم ترقية updated إلى posted، حالة `Estimated` ومصدرها، ومعرّفات السجلات.",
        "- `field_consistency_checks.csv` يسجل كل فحص وعدد المخالفات. إذا ظهر أي إخفاق، يجب مراجعته قبل استهلاك الملف.",
        "",
        "## قاعدة البيانات وإعادة التحليل",
        "",
        sqlite_round_trip_line,
        database_detail_line,
        "- قاعدة المشروع السابقة وأرشيف Parquet غير متاحين في checkout؛ لذلك لا توجد مقارنة تاريخية أو تحقق لقاعدة خارجية ما لم يُمرر ملف `--database-validation-json`. عند غياب هذا الملف تكون الحالة `not_checked`، ولا يُفترض أن قاعدة كاملة أُعيد بناؤها.",
        "- فحص SQLite الداخلي هو اختبار قراءة/إعادة تجميع للملف النهائي، وليس تأكيدًا أن الإعلانات نشطة أو أن حقوق إعادة التوزيع متاحة.",
        "",
        "## سجل التغييرات والملفات الناتجة",
        "",
        "كل تعديل فعلي على أعمدة مشتقة، وكل عملية تحويل/تقدير للراتب، لها سجل صفّي في `cleaning_change_log.csv.gz`؛ ملخص العمليات في `cleaning_change_summary.csv`. التكرارات/outliers غير المحذوفة تسجل كمرشحات مراجعة لا كتغييرات.",
        "",
    ])
    deliverables = summary.get("deliverables", {})
    for label, location in deliverables.items():
        lines.append(f"- **{label}:** `{location}`")
    lines.extend([
        "",
        "## حدود التفسير",
        "",
        "1. كل التقديرات Synthetic/Estimated وليست قيمًا فعلية أو نصيحة مالية؛ قيمتها تتأثر بانحياز عينة الرواتب الفعلية الصغيرة/غير المتجانسة.",
        "2. معدلات FX تاريخية على يوم التدقيق، وليست سعر صرف تاريخ نشر كل إعلان؛ لا يوجد تعديل تضخم أو كلفة معيشة/PPP.",
        "3. يُسجل تاريخ الجمع فقط عند وجود حقل صريح؛ تاريخ الملف في Drive لا يثبت وقت جمع كل إعلان ولا يُستخدم بديلًا عنه.",
        "4. تطابق عنوان/شركة/موقع/رابط يولد candidate فقط. لا تحذف أي صف قبل تأكيد أن الإعلان يمثل الوظيفة نفسها.",
        "5. المصدر الحالي يضم snapshots ذات دلالات زمنية مختلفة؛ وجود السجل لا يعني أنه نشط حاليًا.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def _make_salary_change_log_row(record: Mapping[str, str], original_type: str, method: str) -> dict[str, str]:
    before = _selected_original_salary(record)
    after = {
        "USD": record.get("salary_annual_salary_usd", ""),
        "EGP": record.get("salary_annual_salary_egp", ""),
        "SAR": record.get("salary_annual_salary_sar", ""),
        "USD_range": [record.get("salary_annual_min_usd", ""), record.get("salary_annual_max_usd", "")],
    }
    operation = "synthetic_salary_estimate" if record.get("salary_value_type") == "estimated_synthetic" else "annualization_fx_normalization"
    return {
        "record_id": record.get("record_id", ""),
        "source_file": record.get("source_file", ""),
        "source_row_number": record.get("source_row_number", ""),
        "field_name": "salary_annual_min_point_max_usd_egp_sar",
        "operation": operation,
        "original_value": before,
        "derived_value_json": json.dumps(after, ensure_ascii=False, separators=(",", ":")),
        "method": method,
        "status": record.get("salary_estimation_status", ""),
    }


def finalize_full_audit(
    raw_directory: Path,
    dataset_path: Path,
    report_directory: Path,
    *,
    source_ref: str,
    as_of_date: dt.date,
    fx_policy_path: Path = DEFAULT_FX_POLICY,
    database_validation: Mapping[str, Any] | None = None,
    notebook_path: Path | None = None,
) -> dict[str, Any]:
    raw_directory = raw_directory.resolve()
    dataset_path = dataset_path.resolve()
    report_directory = report_directory.resolve()
    fx_policy_path = fx_policy_path.resolve()
    report_directory.mkdir(parents=True, exist_ok=True)
    fx_policy = _load_fx_policy(fx_policy_path)
    fx_policy["policy_path"] = _workspace_path_label(fx_policy_path)
    if fx_policy["fx_rate_date"] != as_of_date.isoformat():
        raise ValueError("FX rate date must match --as-of-date; do not silently use a different FX date.")
    rates = fx_policy["fx_rates_to_reporting_currency"]
    target_rates = fx_policy["target_currency_rates_from_usd"]
    models, benchmark_report = _build_benchmarks(dataset_path, fx_policy)

    staging = dataset_path.with_name(dataset_path.name + ".finalizing")
    if staging.exists():
        staging.unlink()
    change_log_path = report_directory / "cleaning_change_log.csv.gz"
    change_log_counts: Counter[tuple[str, str]] = Counter()
    salary_source_type_counts: Counter[str] = Counter()
    salary_status_counts: Counter[str] = Counter()
    salary_method_counts: Counter[str] = Counter()
    salary_estimated_added = 0
    salary_missing_before = 0
    salary_missing_after = 0
    salary_actual_converted = 0
    salary_legacy_converted = 0
    salary_source_unverified_converted = 0
    currency_conversion_missing_by_code: Counter[str] = Counter()
    period_conversion_missing_by_code: Counter[str] = Counter()
    row_count = 0
    source_rows = Counter()
    exact_within_source_count = 0

    with gzip.open(dataset_path, "rt", encoding="utf-8", newline="") as input_handle:
        reader = csv.DictReader(input_handle)
        base_fields = reader.fieldnames or []
        output_fields = list(dict.fromkeys([*base_fields, *ADDED_FIELDS]))
        with gzip.open(staging, "wt", encoding="utf-8", newline="", compresslevel=6) as output_handle, gzip.open(change_log_path, "wt", encoding="utf-8", newline="", compresslevel=6) as change_handle:
            writer = csv.DictWriter(output_handle, fieldnames=output_fields, extrasaction="ignore", lineterminator="\n")
            writer.writeheader()
            change_fields = ["record_id", "source_file", "source_row_number", "field_name", "operation", "original_value", "derived_value_json", "method", "status"]
            change_writer = csv.DictWriter(change_handle, fieldnames=change_fields, extrasaction="ignore", lineterminator="\n")
            change_writer.writeheader()
            for source_record in reader:
                row_count += 1
                record = dict(source_record)
                source_file = record.get("source_file", "")
                source_rows[source_file] += 1
                current_type = record.get("salary_value_type", "")
                original_type = record.get("salary_source_value_type", "") if current_type == "estimated_synthetic" else current_type
                original_type = original_type or current_type
                record["salary_source_value_type"] = original_type
                salary_source_type_counts[original_type] += 1
                record["salary_original"] = _selected_original_salary(record)
                record["role_family"] = _role_family(record.get("title_clean", ""), record.get("category_raw", ""))
                record["seniority_band"] = _seniority_band(
                    record.get("title_clean", ""), record.get("experience_raw", ""),
                    record.get("experience_years_min", ""), record.get("experience_years_max", ""),
                )
                location_raw = record.get("location_raw", "")
                record["location_clean"] = cleaner.collapse_whitespace(location_raw) if not _is_missing(location_raw) else ""
                record["location_key"] = _normal_key(record["location_clean"])
                work_mode = _standardize_work_mode(record.get("work_mode_raw", ""), record.get("remote_flag_raw", ""))
                record["work_mode_standardized"] = work_mode
                record["employment_type_standardized"] = _standardize_employment_type(record.get("employment_type_raw", ""))

                # Explicit source-reported salary normalization (known source currency and pay period only).
                annual_values = _salary_values_for_output(record, fx_policy)
                record.update(annual_values)
                if original_type == "actual_reported":
                    status = "Actual"
                    method = "source_reported_annualization_and_fx_conversion"
                    source = f"source_file:{source_file}; source listing not independently rechecked"
                    confidence = "source_reported_not_live_verified"
                    reference_count = ""
                elif original_type == "estimated_legacy_unverified":
                    status = "Estimated"
                    method = "legacy_source_estimate_preserved_not_revalidated"
                    source = "legacy estimate fields/provenance preserved from source row; no live revalidation"
                    confidence = "unverified_legacy"
                    reference_count = ""
                elif original_type == "source_reported_unverified":
                    status = "Unverified"
                    method = "source_reported_numeric_value_provenance_unverified"
                    source = f"source_file:{source_file}; posting/estimate provenance not established"
                    confidence = "unverified_source_value"
                    reference_count = ""
                elif original_type == "not_disclosed":
                    status = "Not disclosed"
                    method = "source_explicitly_withholds_or_negotiates_salary"
                    source = "source non-disclosure; no imputation applied"
                    confidence = "not_applicable"
                    reference_count = ""
                elif original_type == "unparseable_or_no_numeric_amount":
                    status = "Unparseable"
                    method = "source_salary_text_not_safely_parseable"
                    source = "original source text retained; no replacement applied"
                    confidence = "not_applicable"
                    reference_count = ""
                else:
                    status = "Missing"
                    method = "no_synthetic_estimate_available"
                    source = "none"
                    confidence = "not_available"
                    reference_count = ""

                if original_type == "missing":
                    salary_missing_before += 1
                    benchmark = _benchmark_for_record(record, models)
                    if benchmark:
                        salary_estimated_added += 1
                        status = "Estimated"
                        method = benchmark["method"]
                        source = "synthetic internal model using actual source-reported annual salary records only; not an external salary source"
                        confidence = benchmark["confidence"]
                        reference_count = str(benchmark["reference_count"])
                        record["salary_value_type"] = "estimated_synthetic"
                        record["salary_reporting_currency"] = "USD"
                        record["salary_annualized_min_reporting_currency"] = _format_number(benchmark["q1_usd"])
                        record["salary_annualized_max_reporting_currency"] = _format_number(benchmark["q3_usd"])
                        record["salary_annualized_midpoint_reporting_currency"] = _format_number(benchmark["median_usd"])
                        record["salary_annual_min_usd"] = _format_number(benchmark["q1_usd"])
                        record["salary_annual_salary_usd"] = _format_number(benchmark["median_usd"])
                        record["salary_annual_max_usd"] = _format_number(benchmark["q3_usd"])
                        record["salary_annual_min_egp"] = _format_number(benchmark["q1_usd"] * float(target_rates["EGP"]))
                        record["salary_annual_salary_egp"] = _format_number(benchmark["median_usd"] * float(target_rates["EGP"]))
                        record["salary_annual_max_egp"] = _format_number(benchmark["q3_usd"] * float(target_rates["EGP"]))
                        record["salary_annual_min_sar"] = _format_number(benchmark["q1_usd"] * float(target_rates["SAR"]))
                        record["salary_annual_salary_sar"] = _format_number(benchmark["median_usd"] * float(target_rates["SAR"]))
                        record["salary_annual_max_sar"] = _format_number(benchmark["q3_usd"] * float(target_rates["SAR"]))
                        record["salary_estimate_currency_code"] = "USD"
                        record["salary_estimate_range_basis"] = "Q1-Q3 of the matched Actual reference group; synthetic reference spread, not an advertised pay range"
                        record["salary_comparability_status"] = "synthetic estimated annual salary; not employer-reported; see method/reference count/confidence"
                        record["salary_statistics_eligible"] = "no"
                        record["salary_integrity_flags"] = _append_flag(record.get("salary_integrity_flags", ""), "synthetic_salary_estimate_not_actual")
                        existing_flags = record.get("data_quality_flags", "")
                        existing_flags = ";".join(flag for flag in existing_flags.split(";") if flag and flag != "missing_salary_no_imputation")
                        record["data_quality_flags"] = _append_flag(existing_flags, "synthetic_salary_estimate_added_original_salary_preserved")
                    else:
                        salary_missing_after += 1
                        record["salary_estimate_range_basis"] = "no_reference_group_met_minimum_sample_count"
                if original_type == "actual_reported" and not _is_missing(record.get("salary_annual_salary_usd", "")):
                    salary_actual_converted += 1
                elif original_type == "estimated_legacy_unverified" and not _is_missing(record.get("salary_annual_salary_usd", "")):
                    salary_legacy_converted += 1
                elif original_type == "source_reported_unverified" and not _is_missing(record.get("salary_annual_salary_usd", "")):
                    salary_source_unverified_converted += 1

                record["salary_estimation_status"] = status
                record["salary_estimate_currency_code"] = record.get("salary_estimate_currency_code", "") or ("USD" if record.get("salary_value_type") == "estimated_synthetic" else "")
                record["salary_estimation_method"] = method
                record["salary_estimation_source"] = source
                record["salary_estimation_confidence"] = confidence
                record["salary_estimate_reference_count"] = reference_count
                record["salary_estimation_as_of_date"] = as_of_date.isoformat() if status in {"Actual", "Estimated", "Unverified"} else ""
                salary_status_counts[status] += 1
                salary_method_counts[method] += 1
                exact_within_source_count += int(record.get("exact_duplicate_within_source") == "yes")
                if original_type == "missing" and status == "Missing":
                    pass
                if record.get("salary_currency_code") and record.get("salary_annual_salary_usd") == "" and original_type != "missing":
                    currency_conversion_missing_by_code[record["salary_currency_code"]] += 1
                if record.get("salary_period_code") == "UNKNOWN" and record.get("salary_parse_status") in {"parsed_single_amount", "parsed_range", "range_order_reversed"}:
                    period_conversion_missing_by_code[record.get("salary_period_code", "UNKNOWN")] += 1

                # Log changes to derived text fields while retaining the before values in raw columns.
                text_changes = [
                    ("title_clean", record.get("title_raw", ""), record.get("title_clean", ""), "whitespace_normalization"),
                    ("company_clean", record.get("company_raw", ""), record.get("company_clean", ""), "whitespace_normalization"),
                    ("country_standardized", record.get("country_raw", ""), record.get("country_standardized", ""), "explicit_alias_or_whitespace_normalization"),
                    ("location_clean", location_raw, record.get("location_clean", ""), "whitespace_normalization"),
                    ("work_mode_standardized", record.get("work_mode_raw", ""), work_mode, "explicit_conservative_category_mapping"),
                    ("employment_type_standardized", record.get("employment_type_raw", ""), record.get("employment_type_standardized", ""), "explicit_conservative_category_mapping"),
                ]
                for field_name, old_value, new_value, operation in text_changes:
                    if old_value != new_value and not (_is_missing(old_value) and _is_missing(new_value)):
                        change_writer.writerow({
                            "record_id": record.get("record_id", ""), "source_file": source_file,
                            "source_row_number": record.get("source_row_number", ""), "field_name": field_name,
                            "operation": operation, "original_value": old_value,
                            "derived_value_json": json.dumps(new_value, ensure_ascii=False),
                            "method": "derived column only; raw column unchanged", "status": "transformed",
                        })
                        change_log_counts[(field_name, operation)] += 1
                if int(record.get("skill_duplicate_token_count", 0) or 0) > 0:
                    change_writer.writerow({
                        "record_id": record.get("record_id", ""), "source_file": source_file,
                        "source_row_number": record.get("source_row_number", ""), "field_name": "skills_tokens_json",
                        "operation": "exact_duplicate_skill_token_removed_from_derived_list_only",
                        "original_value": record.get("skills_raw", ""),
                        "derived_value_json": record.get("skills_tokens_json", "[]"),
                        "method": "source-specific tokenization + exact casefold/whitespace alias resolution; raw skill string unchanged",
                        "status": "transformed",
                    })
                    change_log_counts[("skills_tokens_json", "exact_duplicate_skill_token_removed_from_derived_list_only")] += 1
                if not _is_missing(record.get("salary_annual_salary_usd", "")):
                    change = _make_salary_change_log_row(record, original_type, method)
                    change_writer.writerow(change)
                    change_log_counts[(change["field_name"], change["operation"])] += 1

                writer.writerow(record)

    if row_count != int(json.loads((report_directory / "cleaning_summary.json").read_text(encoding="utf-8")).get("input_rows", row_count)):
        staging.unlink(missing_ok=True)
        raise AssertionError(f"Output row count {row_count} differs from the source-cleaning summary.")
    os.replace(staging, dataset_path)
    change_summary_path = report_directory / "cleaning_change_summary.csv"
    change_rows = [
        {"field_name": field, "operation": operation, "changed_record_count": count, "raw_source_preserved": "yes", "review_note": "Derived values only; never delete source rows or raw values."}
        for (field, operation), count in sorted(change_log_counts.items())
    ]
    _write_plain_csv(change_summary_path, ["field_name", "operation", "changed_record_count", "raw_source_preserved", "review_note"], change_rows)

    # Reconcile every source file checksum before/after this finalization.
    final_manifest = cleaner._source_manifest(raw_directory)
    source_changed = [item["file"] for item in final_manifest if item["status"] == "available" and item["sha256"] != next((before.get("sha256") for before in json.loads((report_directory / "cleaning_summary.json").read_text(encoding="utf-8")).get("source_manifest", []) if before.get("file") == item["file"]), item["sha256"])]
    if source_changed:
        raise RuntimeError("Raw sources changed during full audit: " + ", ".join(source_changed))

    audit = _quality_pass(raw_directory, dataset_path, report_directory, as_of_date, fx_policy, models, benchmark_report, database_validation)
    total_missing_in_raw = salary_missing_before
    summary_path = report_directory / "cleaning_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["source_ref"] = source_ref
    summary["audit_date"] = as_of_date.isoformat()
    summary["cleaned_dataset_sha256"] = cleaner.sha256_file(dataset_path)
    summary["input_rows"] = row_count
    summary["output_rows"] = audit["rows"]
    summary["rows_dropped"] = row_count - audit["rows"]
    summary["scope"] = "all_declared_sources_available" if audit["raw_summary"]["all_selected_sources_present"] else "partial_sources"
    summary["missing_required_sources"] = [name for name, spec in ((item["file"], item) for item in cleaner.JOB_SOURCE_SPECS) if not (raw_directory / name).is_file() and spec.get("required")]
    summary["salary"] = {
        **summary.get("salary", {}),
        "source_value_type_counts": audit["salary_value_type_counts"],
        "value_type_counts": audit["salary_value_type_counts"],
        "estimation_status_counts": audit["salary_status_counts"],
        "salary_estimation_method_counts": audit["salary_method_counts"],
        "actual_reported_records": audit["salary_value_type_counts"].get("actual_reported", 0),
        "actual_statistics_eligible_records": benchmark_report["benchmark_actual_record_count"],
        "eligible_actual_records_used_for_benchmarks": benchmark_report["benchmark_actual_record_count"],
        "benchmark_actual_count_by_source": benchmark_report["benchmark_count_by_source"],
        "benchmark_actual_count_by_currency": benchmark_report["benchmark_count_by_currency"],
        "legacy_estimate_unverified_records": audit["salary_value_type_counts"].get("estimated_legacy_unverified", 0),
        "source_reported_unverified_records": audit["salary_value_type_counts"].get("source_reported_unverified", 0),
        "synthetic_estimates_added_by_this_run": salary_estimated_added,
        "estimates_added_by_this_run": salary_estimated_added,
        "original_missing_records": total_missing_in_raw,
        "missing_records_after_estimation": salary_missing_after,
        "missing_records": salary_missing_after,
        "annual_salary_available_by_currency": audit["annual_salary_available_counts"],
        "annual_salary_usd_missing": audit["salary_missing"].get("salary_annual_salary_usd_missing", 0),
        "annual_salary_egp_missing": audit["salary_missing"].get("salary_annual_salary_egp_missing", 0),
        "annual_salary_sar_missing": audit["salary_missing"].get("salary_annual_salary_sar_missing", 0),
        "actual_rows_annualized_fx_converted": salary_actual_converted,
        "legacy_estimate_rows_annualized_fx_converted": salary_legacy_converted,
        "source_reported_unverified_rows_annualized_fx_converted": salary_source_unverified_converted,
        "currency_conversion_missing_by_code": dict(currency_conversion_missing_by_code),
        "numeric_rows_with_period_unknown": sum(period_conversion_missing_by_code.values()),
        "fx_rates_applied": fx_policy["fx_rates_to_reporting_currency"],
        "period_annualization_factors": fx_policy["annualization_factors"],
    }
    summary["salary_policy"] = {
        "reporting_currency": "USD",
        "target_currencies": ["USD", "EGP", "SAR"],
        "fx_rate_date": fx_policy["fx_rate_date"],
        "fx_rate_source": fx_policy["fx_rate_source"],
        "annualization_factors": fx_policy["annualization_factors"],
        "fx_policy_path": _workspace_path_label(fx_policy_path),
        "missing_value_estimation": "synthetic hierarchical medians of actual source-reported annual salaries only; each estimate is explicitly marked Estimated/Synthetic with method/confidence/reference count; original salary remains unchanged",
        "salary_history_inflation_or_ppp_adjustment": "none",
        "conversion_note": "All source currencies are first converted to USD, then to EGP/SAR. One audit-date rate is used uniformly; publication date does not set FX date.",
        "benchmark_training": benchmark_report,
    }
    summary["full_data_quality_audit"] = {
        "output_columns_checked": audit["columns"],
        "source_column_count": audit["source_column_count"],
        "type_invalid_values": audit["type_invalid_values"],
        "field_consistency": audit["consistency"],
        "field_consistency_checks": audit["consistency_checks"],
        "duplicate_review": audit["duplicate_report"],
        "database_validation": audit["database_validation"],
        "date_collection_source_columns": audit["raw_summary"]["collection_date_source_columns"],
    }
    summary["source_manifest"] = final_manifest
    summary["source_integrity"] = {
        **summary.get("source_integrity", {}),
        "all_unchanged_during_full_audit": not source_changed,
        "changed_during_full_audit": source_changed,
    }
    summary["sqlite_round_trip"] = audit["database_validation"] if audit["database_validation"].get("status") != "not_checked" else summary.get("sqlite_round_trip", {})
    summary["deliverables"].update({
        "full_cleaned_dataset": _workspace_path_label(dataset_path),
        "raw_source_column_coverage": _workspace_path_label(Path(audit["raw_coverage_path"])),
        "raw_source_type_audit": _workspace_path_label(Path(audit["raw_type_path"])),
        "cleaned_column_coverage": _workspace_path_label(Path(audit["cleaned_coverage_path"])),
        "cleaned_column_type_audit": _workspace_path_label(Path(audit["output_type_audit_path"])),
        "field_coverage_comparison": _workspace_path_label(Path(audit["logical_coverage_path"])),
        "date_quality_audit": _workspace_path_label(Path(audit["date_path"])),
        "missingness_impact": _workspace_path_label(Path(audit["missingness_path"])),
        "country_standardization_audit": _workspace_path_label(Path(audit["country_path"])),
        "role_family_profile": _workspace_path_label(Path(audit["family_path"])),
        "annual_salary_statistics_actual": _workspace_path_label(Path(audit["annual_salary_statistics_path"])),
        "salary_estimate_summary": _workspace_path_label(Path(audit["estimate_summary_path"])),
        "salary_fx_rates_used": _workspace_path_label(Path(audit["fx_path"])),
        "duplicate_review_candidates": str(Path(audit["duplicate_report"]["candidate_file"])),
        "field_consistency_checks": _workspace_path_label(Path(audit["consistency_path"])),
        "cleaning_change_log": _workspace_path_label(change_log_path),
        "cleaning_change_summary": _workspace_path_label(change_summary_path),
        "salary_model_and_fx_policy": _workspace_path_label(report_directory / "salary_model_and_fx_policy.json"),
    })
    summary["profile_outputs"].update({
        "annual_salary_statistics_actual": summary["deliverables"]["annual_salary_statistics_actual"],
        "salary_estimate_summary": summary["deliverables"]["salary_estimate_summary"],
    })
    _write_json(summary_path, summary)
    _write_final_report(report_directory / "final_data_quality_report.md", summary, audit, fx_policy)
    notebook_path = notebook_path or cleaner.DEFAULT_NOTEBOOK_PATH
    _write_notebook(notebook_path, summary, audit)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Finalize a full loss-preserving data-quality audit and salary normalization.")
    parser.add_argument("--raw-data-directory", type=Path, default=PROJECT_ROOT / "data" / "raw")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--report-directory", type=Path, default=DEFAULT_REPORT_DIRECTORY)
    parser.add_argument("--source-ref", default="unspecified")
    parser.add_argument("--as-of-date", type=dt.date.fromisoformat, default=dt.date.today())
    parser.add_argument("--fx-policy-file", type=Path, default=DEFAULT_FX_POLICY)
    parser.add_argument("--database-validation-json", type=Path)
    parser.add_argument("--notebook", type=Path, default=cleaner.DEFAULT_NOTEBOOK_PATH)
    args = parser.parse_args(argv)
    database_validation = json.loads(args.database_validation_json.read_text(encoding="utf-8")) if args.database_validation_json else None
    summary = finalize_full_audit(
        args.raw_data_directory, args.dataset, args.report_directory,
        source_ref=args.source_ref, as_of_date=args.as_of_date,
        fx_policy_path=args.fx_policy_file, database_validation=database_validation,
        notebook_path=args.notebook,
    )
    print(json.dumps({
        "rows": summary["output_rows"],
        "dataset": summary["cleaned_dataset_path"],
        "salary": summary["salary"],
        "full_data_quality_audit": summary["full_data_quality_audit"],
        "deliverables": summary["deliverables"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
