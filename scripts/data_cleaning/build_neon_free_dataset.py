from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import heapq
import io
import json
import re
import sys
import tempfile
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, TextIO

PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
DEFAULT_PROCESSED_DATA_DIRECTORY = PROJECT_ROOT_DIRECTORY / "data" / "processed"
DEFAULT_REFERENCE_DATA_DIRECTORY = PROJECT_ROOT_DIRECTORY / "data" / "reference"
DEFAULT_OUTPUT_DIRECTORY = DEFAULT_PROCESSED_DATA_DIRECTORY / "neon_free"
JOB_INPUT_FILE_NAMES = (
    "jobs_historical_2023_sample.csv.gz",
    "jobs_latest_export_unverified.csv.gz",
    "jobs_other_snapshots_unverified.csv.gz",
)
JOB_SKILLS_INPUT_FILE_NAME = "job_skills.csv.gz"
JOB_OUTPUT_FILE_NAME = "jobs_neon_free.csv.gz"
JOB_SKILLS_OUTPUT_FILE_NAME = "job_skills_neon_free.csv.gz"
SKILL_OBSERVATIONS_OUTPUT_FILE_NAME = "skill_observations_neon_free.csv.gz"
QUALITY_REPORT_FILE_NAME = "neon_free_quality_report.json"
PROFILE_NAME = "neon_free_arab_complete_non_arab_stratified_v1"
SAMPLING_POLICY_VERSION = "sha256_source_country_record_id_v1"
DEFAULT_MAX_NON_ARAB_ROWS_PER_SOURCE_COUNTRY = 5
UNCLASSIFIED_COUNTRY_VALUES = {"", "other/unknown", "remote (anywhere)", "worldwide"}
ONE_GIGABYTE_BYTES = 1_000_000_000
DEFAULT_DATABASE_SIZE_GUARD_BYTES = 800_000_000
STORAGE_ESTIMATE_MULTIPLIER = 5
STORAGE_ESTIMATE_FIXED_OVERHEAD_BYTES = 64 * 1024 * 1024
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

ARAB_COUNTRY_CANONICAL_NAMES = (
    "Algeria",
    "Bahrain",
    "Comoros",
    "Djibouti",
    "Egypt",
    "Iraq",
    "Jordan",
    "Kuwait",
    "Lebanon",
    "Libya",
    "Mauritania",
    "Morocco",
    "Oman",
    "Palestine",
    "Qatar",
    "Saudi Arabia",
    "Somalia",
    "Sudan",
    "Syria",
    "Tunisia",
    "United Arab Emirates",
    "Yemen",
)
ARAB_COUNTRY_LOOKUP = {
    "algeria": "Algeria",
    "bahrain": "Bahrain",
    "comoros": "Comoros",
    "comoro islands": "Comoros",
    "comoros islands": "Comoros",
    "djibouti": "Djibouti",
    "egypt": "Egypt",
    "iraq": "Iraq",
    "jordan": "Jordan",
    "kuwait": "Kuwait",
    "lebanon": "Lebanon",
    "libya": "Libya",
    "mauritania": "Mauritania",
    "morocco": "Morocco",
    "oman": "Oman",
    "palestine": "Palestine",
    "palestinian territories": "Palestine",
    "palestinian territory": "Palestine",
    "state of palestine": "Palestine",
    "qatar": "Qatar",
    "ksa": "Saudi Arabia",
    "saudi arabia": "Saudi Arabia",
    "somalia": "Somalia",
    "sudan": "Sudan",
    "syria": "Syria",
    "syrian arab republic": "Syria",
    "tunisia": "Tunisia",
    "uae": "United Arab Emirates",
    "u a e": "United Arab Emirates",
    "united arab emirates": "United Arab Emirates",
    "yemen": "Yemen",
}
REQUIRED_JOB_COLUMNS = {"record_id", "source_dataset", "source_file", "country"}
REQUIRED_JOB_SKILL_COLUMNS = {
    "record_id",
    "source_dataset",
    "source_file",
    "skill_raw",
    "skill_normalized",
    "skill_id",
}
SKILL_OBSERVATION_COLUMNS = (
    "source_dataset",
    "skill_raw",
    "skill_normalized",
    "occurrence_count",
)


class CountingTextWriter:
    def __init__(self, text_stream: TextIO) -> None:
        self.text_stream = text_stream
        self.byte_count = 0

    def write(self, text: str) -> int:
        self.byte_count += len(text.encode("utf-8"))
        return self.text_stream.write(text)


@contextmanager
def open_input_csv(file_path: Path) -> Iterator[TextIO]:
    if file_path.suffix == ".gz":
        with gzip.open(file_path, "rt", encoding="utf-8-sig", newline="") as text_stream:
            yield text_stream
        return
    with file_path.open("r", encoding="utf-8-sig", newline="") as text_stream:
        yield text_stream


@contextmanager
def open_compressed_csv_writer(file_path: Path) -> Iterator[CountingTextWriter]:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("wb") as binary_stream:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=binary_stream,
            compresslevel=9,
            mtime=0,
        ) as compressed_stream:
            with io.TextIOWrapper(compressed_stream, encoding="utf-8", newline="") as text_stream:
                yield CountingTextWriter(text_stream)


def normalize_country_value(country_value: str) -> str:
    normalized_value = re.sub(r"[\s._-]+", " ", country_value.casefold()).strip()
    return normalized_value.strip(" ,;|/")


def find_arab_country(country_value: str) -> str | None:
    normalized_value = normalize_country_value(country_value)
    canonical_country = ARAB_COUNTRY_LOOKUP.get(normalized_value.strip("()[] "))
    if canonical_country:
        return canonical_country
    for country_part in re.split(r"[,;|/]+", normalized_value):
        canonical_country = ARAB_COUNTRY_LOOKUP.get(country_part.strip("()[] "))
        if canonical_country:
            return canonical_country
    return None


def stable_sample_rank(source_dataset: str, country_stratum: str, record_identifier: str) -> int:
    stable_key = "\0".join(
        (SAMPLING_POLICY_VERSION, source_dataset, country_stratum, record_identifier)
    )
    return int.from_bytes(hashlib.sha256(stable_key.encode("utf-8")).digest()[:8], "big")


def positive_integer(argument_value: str) -> int:
    try:
        parsed_value = int(argument_value)
    except ValueError as parsing_failure:
        raise argparse.ArgumentTypeError("Enter a positive integer") from parsing_failure
    if parsed_value < 1:
        raise argparse.ArgumentTypeError("Enter a positive integer")
    return parsed_value


def report_file_path(file_path: Path) -> str:
    try:
        return file_path.resolve().relative_to(PROJECT_ROOT_DIRECTORY).as_posix()
    except ValueError:
        return file_path.name


def read_csv_headers(file_path: Path) -> list[str]:
    with open_input_csv(file_path) as input_stream:
        header = next(csv.reader(input_stream), [])
    if not header or any(not column_name for column_name in header):
        raise ValueError(f"A non-empty CSV header is required: {file_path}")
    if len(header) != len(set(header)):
        raise ValueError(f"Duplicate CSV header columns are not allowed: {file_path}")
    return header


def read_reference_values(file_path: Path, column_name: str) -> set[str]:
    if not file_path.is_file():
        raise FileNotFoundError(f"Required reference file does not exist: {file_path}")
    with open_input_csv(file_path) as input_stream:
        reader = csv.DictReader(input_stream, strict=True)
        if not reader.fieldnames or column_name not in reader.fieldnames:
            raise ValueError(f"Required column {column_name!r} is missing from {file_path}")
        return {
            row[column_name]
            for row in reader
            if row.get(column_name)
        }


def validate_input_files(
    processed_data_directory: Path,
    reference_data_directory: Path,
) -> tuple[tuple[Path, ...], Path, tuple[str, ...]]:
    job_file_paths = tuple(
        processed_data_directory / file_name
        for file_name in JOB_INPUT_FILE_NAMES
    )
    missing_job_files = [str(file_path) for file_path in job_file_paths if not file_path.is_file()]
    if missing_job_files:
        raise FileNotFoundError(f"Required full job exports are missing: {missing_job_files}")
    job_skill_file_path = processed_data_directory / JOB_SKILLS_INPUT_FILE_NAME
    if not job_skill_file_path.is_file():
        raise FileNotFoundError(f"Required job-skill export is missing: {job_skill_file_path}")

    job_headers = tuple(read_csv_headers(file_path) for file_path in job_file_paths)
    if any(header != job_headers[0] for header in job_headers[1:]):
        raise ValueError("The three job exports must have identical CSV columns in the same order")
    missing_job_columns = sorted(REQUIRED_JOB_COLUMNS.difference(job_headers[0]))
    if missing_job_columns:
        raise ValueError(f"Job exports are missing required columns: {missing_job_columns}")

    job_skill_headers = read_csv_headers(job_skill_file_path)
    missing_job_skill_columns = sorted(REQUIRED_JOB_SKILL_COLUMNS.difference(job_skill_headers))
    if missing_job_skill_columns:
        raise ValueError(f"The job-skill export is missing required columns: {missing_job_skill_columns}")

    read_csv_headers(reference_data_directory / "skill_catalog.csv")
    read_csv_headers(reference_data_directory / "skill_aliases.csv")
    read_csv_headers(reference_data_directory / "learning_resources.csv")
    return job_file_paths, job_skill_file_path, job_headers[0]


def select_job_records(
    job_file_paths: tuple[Path, ...],
    maximum_non_arab_rows_per_source_country: int,
) -> tuple[set[str], dict[str, object]]:
    source_row_counts: Counter[str] = Counter()
    arab_row_counts_by_country: Counter[str] = Counter()
    arab_row_counts_by_source: Counter[str] = Counter()
    non_arab_row_counts_by_source: Counter[str] = Counter()
    unclassified_row_counts_by_source: Counter[str] = Counter()
    unclassified_country_counts: Counter[str] = Counter()
    unclassified_country_labels: dict[str, str] = {}
    non_arab_stratum_counts: Counter[tuple[str, str]] = Counter()
    non_arab_stratum_labels: dict[tuple[str, str], str] = {}
    non_arab_candidate_heaps: dict[tuple[str, str], list[tuple[int, str]]] = {}
    arab_job_record_ids: set[str] = set()
    unclassified_job_record_ids: set[str] = set()

    for job_file_path in job_file_paths:
        with open_input_csv(job_file_path) as input_stream:
            reader = csv.DictReader(input_stream, strict=True)
            for row in reader:
                record_identifier = (row.get("record_id") or "").strip()
                source_dataset = (row.get("source_dataset") or "").strip()
                if not record_identifier or not source_dataset:
                    raise ValueError(
                        f"Missing record_id or source_dataset in {job_file_path.name}"
                    )
                source_row_counts[source_dataset] += 1
                country_value = (row.get("country") or "").strip()
                canonical_arab_country = find_arab_country(country_value)
                if canonical_arab_country:
                    if record_identifier in arab_job_record_ids:
                        raise ValueError(f"Duplicate Arabic job record_id: {record_identifier}")
                    arab_job_record_ids.add(record_identifier)
                    arab_row_counts_by_country[canonical_arab_country] += 1
                    arab_row_counts_by_source[source_dataset] += 1
                    continue

                country_stratum = normalize_country_value(country_value)
                if country_stratum in UNCLASSIFIED_COUNTRY_VALUES:
                    if record_identifier in arab_job_record_ids or record_identifier in unclassified_job_record_ids:
                        raise ValueError(f"Duplicate unclassified job record_id: {record_identifier}")
                    unclassified_job_record_ids.add(record_identifier)
                    unclassified_row_counts_by_source[source_dataset] += 1
                    unclassified_country_counts[country_stratum] += 1
                    unclassified_country_labels.setdefault(country_stratum, country_value)
                    continue

                non_arab_row_counts_by_source[source_dataset] += 1
                stratum_key = (source_dataset, country_stratum)
                non_arab_stratum_counts[stratum_key] += 1
                non_arab_stratum_labels.setdefault(stratum_key, country_value)
                candidate_heap = non_arab_candidate_heaps.setdefault(stratum_key, [])
                rank = stable_sample_rank(source_dataset, country_stratum, record_identifier)
                candidate = (-rank, record_identifier)
                if len(candidate_heap) < maximum_non_arab_rows_per_source_country:
                    heapq.heappush(candidate_heap, candidate)
                elif rank < -candidate_heap[0][0]:
                    heapq.heapreplace(candidate_heap, candidate)

    selected_non_arab_record_ids: set[str] = set()
    stratum_report: list[dict[str, object]] = []
    retained_non_arab_counts_by_source: Counter[str] = Counter()
    for stratum_key in sorted(non_arab_stratum_counts):
        source_dataset, country_stratum = stratum_key
        candidate_heap = non_arab_candidate_heaps[stratum_key]
        retained_row_count = len(candidate_heap)
        retained_non_arab_counts_by_source[source_dataset] += retained_row_count
        stratum_report.append(
            {
                "source_dataset": source_dataset,
                "country": non_arab_stratum_labels[stratum_key],
                "country_normalized": country_stratum,
                "available_rows": non_arab_stratum_counts[stratum_key],
                "retained_rows": retained_row_count,
                "omitted_rows": non_arab_stratum_counts[stratum_key] - retained_row_count,
            }
        )
        for _, record_identifier in candidate_heap:
            if (
                record_identifier in arab_job_record_ids
                or record_identifier in unclassified_job_record_ids
                or record_identifier in selected_non_arab_record_ids
            ):
                raise ValueError(f"Duplicate selected job record_id: {record_identifier}")
            selected_non_arab_record_ids.add(record_identifier)

    selected_job_record_ids = (
        arab_job_record_ids
        | unclassified_job_record_ids
        | selected_non_arab_record_ids
    )
    source_dataset_names = sorted(source_row_counts)
    source_row_summary = {
        source_dataset: {
            "available_rows": source_row_counts[source_dataset],
            "arab_rows_retained": arab_row_counts_by_source[source_dataset],
            "unclassified_geography_rows_retained": unclassified_row_counts_by_source[source_dataset],
            "non_arab_rows_available": non_arab_row_counts_by_source[source_dataset],
            "non_arab_rows_retained": retained_non_arab_counts_by_source[source_dataset],
            "omitted_rows": (
                non_arab_row_counts_by_source[source_dataset]
                - retained_non_arab_counts_by_source[source_dataset]
            ),
        }
        for source_dataset in source_dataset_names
    }
    selection_report = {
        "input_job_rows": sum(source_row_counts.values()),
        "retained_job_rows": len(selected_job_record_ids),
        "retained_arab_job_rows": len(arab_job_record_ids),
        "retained_unclassified_geography_rows": len(unclassified_job_record_ids),
        "retained_unclassified_rows_by_country_value": {
            "(blank)" if not unclassified_country_labels[country_value] else unclassified_country_labels[country_value]: unclassified_country_counts[country_value]
            for country_value in sorted(unclassified_country_counts)
        },
        "retained_non_arab_job_rows": len(selected_non_arab_record_ids),
        "retained_arab_rows_by_country": {
            country_name: arab_row_counts_by_country[country_name]
            for country_name in ARAB_COUNTRY_CANONICAL_NAMES
        },
        "source_datasets": source_row_summary,
        "non_arab_strata_count": len(stratum_report),
        "non_arab_strata": stratum_report,
    }
    if len(arab_job_record_ids) != sum(arab_row_counts_by_country.values()):
        raise ValueError("Arabic job row counts do not match unique Arabic record IDs")
    return selected_job_record_ids, selection_report


def write_selected_jobs(
    job_file_paths: tuple[Path, ...],
    job_headers: tuple[str, ...],
    selected_job_record_ids: set[str],
    output_file_path: Path,
) -> tuple[int, int, dict[str, tuple[str, str]], Counter[str], Counter[str], set[str]]:
    remaining_job_record_ids = set(selected_job_record_ids)
    selected_job_metadata: dict[str, tuple[str, str]] = {}
    retained_job_rows_by_source: Counter[str] = Counter()
    retained_arab_job_rows_by_country: Counter[str] = Counter()
    retained_arab_job_record_ids: set[str] = set()
    total_written_job_rows = 0

    with open_compressed_csv_writer(output_file_path) as output_stream:
        writer = csv.DictWriter(
            output_stream,
            fieldnames=job_headers,
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        for job_file_path in job_file_paths:
            with open_input_csv(job_file_path) as input_stream:
                reader = csv.DictReader(input_stream, strict=True)
                if reader.fieldnames != list(job_headers):
                    raise ValueError(f"Job header changed while reading {job_file_path.name}")
                for row in reader:
                    record_identifier = (row.get("record_id") or "").strip()
                    if record_identifier not in selected_job_record_ids:
                        continue
                    if record_identifier not in remaining_job_record_ids:
                        raise ValueError(f"Duplicate selected job record_id: {record_identifier}")
                    remaining_job_record_ids.remove(record_identifier)
                    source_dataset = (row.get("source_dataset") or "").strip()
                    source_file = (row.get("source_file") or "").strip()
                    selected_job_metadata[record_identifier] = (source_dataset, source_file)
                    retained_job_rows_by_source[source_dataset] += 1
                    canonical_arab_country = find_arab_country((row.get("country") or "").strip())
                    if canonical_arab_country:
                        retained_arab_job_rows_by_country[canonical_arab_country] += 1
                        retained_arab_job_record_ids.add(record_identifier)
                    writer.writerow(row)
                    total_written_job_rows += 1
        if remaining_job_record_ids:
            missing_identifiers = sorted(remaining_job_record_ids)[:10]
            raise ValueError(f"Selected job rows disappeared from inputs: {missing_identifiers}")
        uncompressed_copy_bytes = output_stream.byte_count

    if total_written_job_rows != len(selected_job_record_ids):
        raise ValueError("The selected job row count does not match the unique selected record IDs")
    return (
        total_written_job_rows,
        uncompressed_copy_bytes,
        selected_job_metadata,
        retained_job_rows_by_source,
        retained_arab_job_rows_by_country,
        retained_arab_job_record_ids,
    )


def write_selected_job_skills(
    job_skill_input_path: Path,
    selected_job_metadata: dict[str, tuple[str, str]],
    arab_job_record_ids: set[str],
    skill_catalog_identifiers: set[str],
    skill_alias_identifiers: set[str],
    output_file_path: Path,
    temporary_output_directory: Path,
) -> tuple[int, int, int, int, Counter[str], dict[str, object]]:
    job_skill_headers = read_csv_headers(job_skill_input_path)
    skill_observation_counts: dict[tuple[str, str], list[object]] = {}
    job_record_ids_with_skills: set[str] = set()
    relationship_primary_keys: set[tuple[str, str]] = set()
    missing_skill_identifiers: set[str] = set()
    missing_skill_aliases: set[str] = set()
    job_skill_rows_by_source: Counter[str] = Counter()
    total_written_job_skill_rows = 0
    arab_job_skill_row_count = 0

    with open_compressed_csv_writer(output_file_path) as output_stream:
        writer = csv.DictWriter(
            output_stream,
            fieldnames=job_skill_headers,
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        with open_input_csv(job_skill_input_path) as input_stream:
            reader = csv.DictReader(input_stream, strict=True)
            if reader.fieldnames != job_skill_headers:
                raise ValueError("The job-skill header changed while reading the input")
            for row in reader:
                record_identifier = (row.get("record_id") or "").strip()
                expected_job_metadata = selected_job_metadata.get(record_identifier)
                if expected_job_metadata is None:
                    continue
                actual_job_metadata = (
                    (row.get("source_dataset") or "").strip(),
                    (row.get("source_file") or "").strip(),
                )
                if actual_job_metadata != expected_job_metadata:
                    raise ValueError(
                        f"Job-skill source metadata does not match job {record_identifier}"
                    )
                skill_identifier = (row.get("skill_id") or "").strip()
                normalized_skill_label = (row.get("skill_normalized") or "").strip()
                if skill_identifier not in skill_catalog_identifiers:
                    missing_skill_identifiers.add(skill_identifier)
                if normalized_skill_label not in skill_alias_identifiers:
                    missing_skill_aliases.add(normalized_skill_label)
                primary_key = (record_identifier, skill_identifier)
                if primary_key in relationship_primary_keys:
                    raise ValueError(f"Duplicate selected job-skill relationship: {primary_key}")
                relationship_primary_keys.add(primary_key)
                source_dataset = actual_job_metadata[0]
                observation_key = (source_dataset, normalized_skill_label)
                observation = skill_observation_counts.get(observation_key)
                if observation is None:
                    observation = [row.get("skill_raw") or "", 0]
                    skill_observation_counts[observation_key] = observation
                observation[1] = int(observation[1]) + 1
                job_record_ids_with_skills.add(record_identifier)
                if record_identifier in arab_job_record_ids:
                    arab_job_skill_row_count += 1
                job_skill_rows_by_source[source_dataset] += 1
                writer.writerow(row)
                total_written_job_skill_rows += 1
        uncompressed_copy_bytes = output_stream.byte_count

    if missing_skill_identifiers:
        raise ValueError(
            "Selected job-skill rows reference skill IDs absent from skill_catalog.csv: "
            f"{sorted(missing_skill_identifiers)[:10]}"
        )
    if missing_skill_aliases:
        raise ValueError(
            "Selected job-skill rows reference normalized labels absent from skill_aliases.csv: "
            f"{sorted(missing_skill_aliases)[:10]}"
        )

    skill_observation_output_path = temporary_output_directory / SKILL_OBSERVATIONS_OUTPUT_FILE_NAME
    with open_compressed_csv_writer(skill_observation_output_path) as output_stream:
        writer = csv.DictWriter(
            output_stream,
            fieldnames=SKILL_OBSERVATION_COLUMNS,
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        for (source_dataset, normalized_skill_label), observation in sorted(skill_observation_counts.items()):
            writer.writerow(
                {
                    "source_dataset": source_dataset,
                    "skill_raw": observation[0],
                    "skill_normalized": normalized_skill_label,
                    "occurrence_count": observation[1],
                }
            )
        skill_observation_uncompressed_copy_bytes = output_stream.byte_count

    return (
        total_written_job_skill_rows,
        arab_job_skill_row_count,
        uncompressed_copy_bytes,
        len(job_record_ids_with_skills),
        job_skill_rows_by_source,
        {
            "counts": skill_observation_counts,
            "uncompressed_copy_bytes": skill_observation_uncompressed_copy_bytes,
        },
    )


def build_neon_free_dataset(
    processed_data_directory: Path = DEFAULT_PROCESSED_DATA_DIRECTORY,
    reference_data_directory: Path = DEFAULT_REFERENCE_DATA_DIRECTORY,
    output_directory: Path = DEFAULT_OUTPUT_DIRECTORY,
    maximum_non_arab_rows_per_source_country: int = DEFAULT_MAX_NON_ARAB_ROWS_PER_SOURCE_COUNTRY,
) -> dict[str, object]:
    if maximum_non_arab_rows_per_source_country < 1:
        raise ValueError("maximum_non_arab_rows_per_source_country must be a positive integer")

    processed_data_directory = processed_data_directory.resolve()
    reference_data_directory = reference_data_directory.resolve()
    output_directory = output_directory.resolve()
    job_file_paths, job_skill_input_path, job_headers = validate_input_files(
        processed_data_directory,
        reference_data_directory,
    )
    selected_job_record_ids, selection_report = select_job_records(
        job_file_paths,
        maximum_non_arab_rows_per_source_country,
    )
    skill_catalog_identifiers = read_reference_values(
        reference_data_directory / "skill_catalog.csv",
        "skill_id",
    )
    skill_alias_identifiers = read_reference_values(
        reference_data_directory / "skill_aliases.csv",
        "alias_normalized",
    )

    output_directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".neon_free_build_", dir=output_directory) as temporary_name:
        temporary_output_directory = Path(temporary_name)
        temporary_jobs_output_path = temporary_output_directory / JOB_OUTPUT_FILE_NAME
        temporary_job_skills_output_path = temporary_output_directory / JOB_SKILLS_OUTPUT_FILE_NAME
        temporary_quality_report_path = temporary_output_directory / QUALITY_REPORT_FILE_NAME
        (
            written_job_rows,
            job_uncompressed_copy_bytes,
            selected_job_metadata,
            retained_job_rows_by_source,
            retained_arab_job_rows_by_country,
            retained_arab_job_record_ids,
        ) = write_selected_jobs(
            job_file_paths,
            job_headers,
            selected_job_record_ids,
            temporary_jobs_output_path,
        )
        (
            written_job_skill_rows,
            arab_job_skill_rows,
            job_skill_uncompressed_copy_bytes,
            selected_jobs_with_skills,
            job_skill_rows_by_source,
            skill_observation_report,
        ) = write_selected_job_skills(
            job_skill_input_path,
            selected_job_metadata,
            retained_arab_job_record_ids,
            skill_catalog_identifiers,
            skill_alias_identifiers,
            temporary_job_skills_output_path,
            temporary_output_directory,
        )
        skill_observation_output_path = temporary_output_directory / SKILL_OBSERVATIONS_OUTPUT_FILE_NAME
        skill_observation_counts = skill_observation_report["counts"]
        skill_observation_uncompressed_copy_bytes = skill_observation_report[
            "uncompressed_copy_bytes"
        ]
        if not isinstance(skill_observation_counts, dict):
            raise TypeError("Skill observation aggregation must be a dictionary")

        if written_job_rows != selection_report["retained_job_rows"]:
            raise ValueError("Written job rows do not match the selection report")
        if selection_report["retained_arab_job_rows"] != sum(retained_arab_job_rows_by_country.values()):
            raise ValueError("Not all selected Arabic job rows were retained in the new output")

        retained_source_summary = selection_report["source_datasets"]
        if not isinstance(retained_source_summary, dict):
            raise TypeError("Source dataset summary must be a dictionary")
        for source_dataset, source_summary in retained_source_summary.items():
            if not isinstance(source_summary, dict):
                raise TypeError("Source dataset summary rows must be dictionaries")
            source_summary["job_rows_written"] = retained_job_rows_by_source[source_dataset]
            source_summary["job_skill_rows_written"] = job_skill_rows_by_source[source_dataset]

        reference_file_paths = (
            reference_data_directory / "skill_catalog.csv",
            reference_data_directory / "skill_aliases.csv",
            reference_data_directory / "learning_resources.csv",
        )
        reference_copy_bytes = sum(file_path.stat().st_size for file_path in reference_file_paths)
        total_uncompressed_copy_bytes = (
            job_uncompressed_copy_bytes
            + job_skill_uncompressed_copy_bytes
            + skill_observation_uncompressed_copy_bytes
            + reference_copy_bytes
        )
        estimated_database_size_bytes = (
            total_uncompressed_copy_bytes * STORAGE_ESTIMATE_MULTIPLIER
            + STORAGE_ESTIMATE_FIXED_OVERHEAD_BYTES
        )
        if estimated_database_size_bytes >= DEFAULT_DATABASE_SIZE_GUARD_BYTES:
            raise ValueError(
                "The conservative database-size planning estimate reaches the 800 MB load guard. "
                "Lower the non-Arab sample cap before generating load files."
            )

        output_files = {
            "jobs": {
                "path": report_file_path(output_directory / JOB_OUTPUT_FILE_NAME),
                "rows": written_job_rows,
                "compressed_bytes": temporary_jobs_output_path.stat().st_size,
                "uncompressed_copy_bytes": job_uncompressed_copy_bytes,
            },
            "job_skills": {
                "path": report_file_path(output_directory / JOB_SKILLS_OUTPUT_FILE_NAME),
                "rows": written_job_skill_rows,
                "compressed_bytes": temporary_job_skills_output_path.stat().st_size,
                "uncompressed_copy_bytes": job_skill_uncompressed_copy_bytes,
            },
            "skill_observations": {
                "path": report_file_path(output_directory / SKILL_OBSERVATIONS_OUTPUT_FILE_NAME),
                "rows": len(skill_observation_counts),
                "compressed_bytes": skill_observation_output_path.stat().st_size,
                "uncompressed_copy_bytes": skill_observation_uncompressed_copy_bytes,
            },
        }
        quality_report: dict[str, object] = {
            "profile": PROFILE_NAME,
            "generated_by": "scripts/data_cleaning/build_neon_free_dataset.py",
            "selection_policy": {
                "arab_countries": list(ARAB_COUNTRY_CANONICAL_NAMES),
                "arab_country_aliases": sorted(ARAB_COUNTRY_LOOKUP),
                "arab_country_rows": "Retain every job row whose country value matches an Arab League member country or a listed alias.",
                "unclassified_geography_rows": (
                    "Retain all rows with a blank country, Other/Unknown, Remote (Anywhere), or Worldwide label in full; "
                    "their geography is not treated as non-Arab without evidence."
                ),
                "unclassified_country_values_retained_in_full": selection_report[
                    "retained_unclassified_rows_by_country_value"
                ],
                "non_arab_rows": (
                    "Retain at most the configured row cap from every (source_dataset, country) stratum. "
                    "Select deterministically by the smallest SHA-256 ranks of source_dataset, normalized country, and record_id."
                ),
                "maximum_non_arab_rows_per_source_country": maximum_non_arab_rows_per_source_country,
                "sampling_policy_version": SAMPLING_POLICY_VERSION,
                "cross_source_deduplication": "Not performed; source rows remain distinct.",
                "arab_job_rows_dropped": 0,
                "source_job_rows": selection_report["input_job_rows"],
                "retained_job_rows": selection_report["retained_job_rows"],
                "retained_arab_job_rows": selection_report["retained_arab_job_rows"],
                "retained_unclassified_geography_rows": selection_report[
                    "retained_unclassified_geography_rows"
                ],
                "retained_non_arab_job_rows": selection_report["retained_non_arab_job_rows"],
                "retained_arab_rows_by_country": selection_report["retained_arab_rows_by_country"],
                "source_datasets": selection_report["source_datasets"],
                "non_arab_strata_count": selection_report["non_arab_strata_count"],
                "non_arab_strata": selection_report["non_arab_strata"],
            },
            "skill_relationship_policy": {
                "job_skill_rows": "Retain every source job-skill relationship for each selected job, including every retained Arab job.",
                "skill_observations": "Recalculate per-source normalized-skill counts from the retained job-skill rows.",
                "selected_jobs_with_skills": selected_jobs_with_skills,
                "selected_jobs_without_skills": written_job_rows - selected_jobs_with_skills,
                "job_skill_rows": written_job_skill_rows,
                "arab_job_skill_rows": arab_job_skill_rows,
                "other_retained_job_skill_rows": written_job_skill_rows - arab_job_skill_rows,
                "skill_observation_rows": len(skill_observation_counts),
            },
            "database_storage_estimate": {
                "formula": (
                    f"{STORAGE_ESTIMATE_MULTIPLIER} times total uncompressed COPY bytes plus "
                    f"{STORAGE_ESTIMATE_FIXED_OVERHEAD_BYTES} bytes fixed overhead."
                ),
                "estimate_caveat": (
                    "This conservative planning proxy is not a PostgreSQL measurement or guaranteed upper bound; "
                    "verify actual database and Neon project usage after import."
                ),
                "is_planning_estimate_only": True,
                "is_measured_neon_storage": False,
                "uncompressed_copy_bytes_including_references": total_uncompressed_copy_bytes,
                "estimated_database_size_bytes": estimated_database_size_bytes,
                "estimated_database_size_megabytes_decimal": round(
                    estimated_database_size_bytes / 1_000_000,
                    2,
                ),
                "neon_free_target_bytes": ONE_GIGABYTE_BYTES,
                "load_guard_bytes": DEFAULT_DATABASE_SIZE_GUARD_BYTES,
                "actual_neon_database_size_bytes": None,
                "verification_required_after_import": (
                    "Measure pg_database_size and pg_total_relation_size after loading; "
                    "confirm the project's actual quota and usage in the Neon dashboard."
                ),
            },
            "input_files": {
                "job_exports": [file_path.name for file_path in job_file_paths],
                "job_skills": job_skill_input_path.name,
                "reference_csv_bytes_in_estimate": [file_path.name for file_path in reference_file_paths],
            },
            "outputs": output_files,
        }
        temporary_quality_report_path.write_text(
            json.dumps(quality_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        for temporary_file_path in temporary_output_directory.iterdir():
            final_output_path = output_directory / temporary_file_path.name
            temporary_file_path.replace(final_output_path)

    return quality_report


def main() -> int:
    command_line_parser = argparse.ArgumentParser(
        description="Build a Neon Free job dataset retaining every Arab-country job and a stratified international sample"
    )
    command_line_parser.add_argument(
        "--processed-data-directory",
        type=Path,
        default=DEFAULT_PROCESSED_DATA_DIRECTORY,
    )
    command_line_parser.add_argument(
        "--reference-data-directory",
        type=Path,
        default=DEFAULT_REFERENCE_DATA_DIRECTORY,
    )
    command_line_parser.add_argument(
        "--output-directory",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
    )
    command_line_parser.add_argument(
        "--maximum-non-arab-rows-per-source-country",
        type=positive_integer,
        default=DEFAULT_MAX_NON_ARAB_ROWS_PER_SOURCE_COUNTRY,
    )
    command_line_arguments = command_line_parser.parse_args()

    try:
        quality_report = build_neon_free_dataset(
            command_line_arguments.processed_data_directory,
            command_line_arguments.reference_data_directory,
            command_line_arguments.output_directory,
            command_line_arguments.maximum_non_arab_rows_per_source_country,
        )
    except (OSError, UnicodeError, csv.Error, ValueError) as build_failure:
        raise SystemExit(f"Neon Free dataset build failed: {build_failure}") from None

    print(json.dumps(quality_report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
