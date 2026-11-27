import argparse
import csv as comma_separated_values
import json as json_serialization
from pathlib import Path
from urllib.parse import urlparse as parse_uniform_resource_locator


project_root_directory = Path(__file__).resolve().parents[2]
default_learning_resources_file = project_root_directory / "data" / "reference" / "learning_resources.json"
default_skill_curation_file = project_root_directory / "data" / "reference" / "skill_curation.json"
default_learning_resources_csv_file = project_root_directory / "data" / "reference" / "learning_resources.csv"
allowed_learning_resource_cost_statuses = {
    "free_verified",
    "some_free_options",
    "conditional_or_mixed",
    "cost_unverified",
}
learning_resource_field_names = [
    "resource_id",
    "title",
    "provider",
    "resource_type",
    "skill_ids",
    "languages",
    "level",
    "access_status",
    "cost_status",
    "account_requirement",
    "credential",
    "resource_url",
    "verification_status",
    "verified_on",
    "notes",
]


def main() -> int:
    command_line_parser = argparse.ArgumentParser(
        description="Validate and export the curated learning-resource collection"
    )
    command_line_parser.add_argument(
        "--learning-resources-file",
        dest="learning_resources_file",
        type=Path,
        default=default_learning_resources_file,
    )
    command_line_parser.add_argument(
        "--skill-curation-file",
        dest="skill_curation_file",
        type=Path,
        default=default_skill_curation_file,
    )
    command_line_parser.add_argument(
        "--output-file",
        dest="output_file",
        type=Path,
        default=default_learning_resources_csv_file,
    )
    command_line_arguments = command_line_parser.parse_args()

    learning_resource_document = json_serialization.loads(
        command_line_arguments.learning_resources_file.resolve().read_text(encoding="utf-8")
    )
    skill_curation_document = json_serialization.loads(
        command_line_arguments.skill_curation_file.resolve().read_text(encoding="utf-8")
    )
    curated_skill_identifiers = {
        curated_skill["skill_id"]
        for curated_skill in skill_curation_document.get("skills", [])
    }
    learning_resources = learning_resource_document.get("resources", [])
    seen_resource_identifiers: set[str] = set()
    learning_resource_records: list[dict[str, str]] = []

    for resource_number, learning_resource in enumerate(learning_resources, start=1):
        resource_identifier = str(learning_resource.get("resource_id", "")).strip()
        if not resource_identifier or resource_identifier in seen_resource_identifiers:
            raise ValueError(
                f"Missing or duplicate resource identifier at item {resource_number}: "
                f"{resource_identifier!r}"
            )
        seen_resource_identifiers.add(resource_identifier)

        missing_field_names = [
            field_name
            for field_name in learning_resource_field_names
            if field_name not in learning_resource or learning_resource[field_name] in (None, "")
        ]
        if missing_field_names:
            raise ValueError(
                f"Resource {resource_identifier} is missing required fields: {missing_field_names}"
            )
        if learning_resource["cost_status"] not in allowed_learning_resource_cost_statuses:
            raise ValueError(
                f"Resource {resource_identifier} has unsupported cost status: "
                f"{learning_resource['cost_status']!r}"
            )

        unrecognized_skill_identifiers = (
            set(learning_resource["skill_ids"]) - curated_skill_identifiers
        )
        if unrecognized_skill_identifiers:
            raise ValueError(
                f"Resource {resource_identifier} references unknown skill identifiers: "
                f"{sorted(unrecognized_skill_identifiers)}"
            )
        if len(learning_resource["skill_ids"]) != len(set(learning_resource["skill_ids"])):
            raise ValueError(f"Resource {resource_identifier} repeats a skill identifier")

        parsed_resource_address = parse_uniform_resource_locator(
            learning_resource["resource_url"]
        )
        if parsed_resource_address.scheme != "https" or not parsed_resource_address.netloc:
            raise ValueError(f"Resource {resource_identifier} must have an HTTPS address")

        learning_resource_records.append(
            {
                field_name: ";".join(learning_resource[field_name])
                if isinstance(learning_resource[field_name], list)
                else str(learning_resource[field_name])
                for field_name in learning_resource_field_names
            }
        )

    output_file_path = command_line_arguments.output_file.resolve()
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    with output_file_path.open("w", encoding="utf-8", newline="") as output_file_handle:
        comma_separated_values_writer = comma_separated_values.DictWriter(
            output_file_handle,
            fieldnames=learning_resource_field_names,
            lineterminator="\n",
        )
        comma_separated_values_writer.writeheader()
        comma_separated_values_writer.writerows(learning_resource_records)

    displayed_output_path = (
        output_file_path.relative_to(project_root_directory)
        if output_file_path.is_relative_to(project_root_directory)
        else output_file_path
    )
    print(
        json_serialization.dumps(
            {
                "resource_rows": len(learning_resource_records),
                "path": str(displayed_output_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
