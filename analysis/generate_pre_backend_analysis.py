from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plot
import numpy as numerical
import pandas as pandas
import seaborn as statistical_graphics

PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_PATH = PROJECT_ROOT_DIRECTORY / "data" / "processed" / "job_market.sqlite3"
DEFAULT_OUTPUT_DIRECTORY = PROJECT_ROOT_DIRECTORY / "analysis" / "reports" / "pre_backend"
SQL_DIRECTORY = PROJECT_ROOT_DIRECTORY / "analysis" / "sql"
QUERY_FILES = {
    "dataset_profile": "01_dataset_profile.sql",
    "source_coverage": "02_source_coverage.sql",
    "field_coverage": "03_field_coverage.sql",
    "top_skills": "04_top_skills.sql",
    "top_exact_titles": "05_top_exact_titles.sql",
    "country_profile": "06_country_profile.sql",
    "historical_2023_monthly": "07_historical_2023_monthly.sql",
    "salary_feasibility": "08_salary_feasibility.sql",
    "model_feasibility": "09_model_feasibility.sql",
    "arab_market_skill_demand": "10_arab_vs_other_market_skills.sql",
    "work_mode_flags": "11_work_mode_flags.sql",
    "exact_duplicate_counts": "12_exact_duplicate_counts.sql",
    "learning_resource_verification": "13_learning_resource_verification.sql",
    "skill_curation_coverage": "14_skill_curation_coverage.sql",
    "merged_arab_country_coverage": "15_merged_arab_country_coverage.sql",
    "role_country_distribution": "16_role_country_distribution.sql",
    "role_skill_demand": "17_role_skill_demand.sql",
    "role_country_skill_demand": "18_role_country_skill_demand.sql",
    "salary_role_country_coverage": "19_salary_role_country_coverage.sql",
}
ARAB_COUNTRY_NAMES = {
    "algeria",
    "bahrain",
    "comoros",
    "djibouti",
    "egypt",
    "iraq",
    "jordan",
    "kuwait",
    "lebanon",
    "libya",
    "mauritania",
    "morocco",
    "oman",
    "palestine",
    "qatar",
    "saudi arabia",
    "somalia",
    "sudan",
    "syria",
    "tunisia",
    "united arab emirates",
    "yemen",
}


def read_only_connection(database_path: Path) -> sqlite3.Connection:
    database_uri = f"{database_path.resolve().as_uri()}?mode=ro"
    return sqlite3.connect(database_uri, uri=True)


def run_analysis_queries(connection: sqlite3.Connection) -> dict[str, pandas.DataFrame]:
    query_results = {}
    for query_name, query_file_name in QUERY_FILES.items():
        query_path = SQL_DIRECTORY / query_file_name
        query_sql = query_path.read_text(encoding="utf-8")
        query_results[query_name] = pandas.read_sql_query(query_sql, connection)
    return query_results


def save_aggregate_tables(query_results: dict[str, pandas.DataFrame], output_directory: Path) -> None:
    for query_name, result_table in query_results.items():
        result_table.to_csv(output_directory / f"{query_name}.csv", index=False, encoding="utf-8")


def markdown_table(dataframe: pandas.DataFrame, maximum_rows: int | None = None) -> str:
    displayed_dataframe = dataframe.head(maximum_rows) if maximum_rows is not None else dataframe
    displayed_dataframe = displayed_dataframe.fillna("").astype(str)
    column_names = [str(column_name).replace("|", "\\|") for column_name in displayed_dataframe.columns]
    header_row = "| " + " | ".join(column_names) + " |"
    separator_row = "| " + " | ".join("---" for _ in column_names) + " |"
    data_rows = [
        "| " + " | ".join(value.replace("|", "\\|").replace("\n", " ") for value in row) + " |"
        for row in displayed_dataframe.itertuples(index=False, name=None)
    ]
    return "\n".join([header_row, separator_row, *data_rows])


def write_bar_chart(
    dataframe: pandas.DataFrame,
    output_path: Path,
    category_column: str,
    value_column: str,
    title: str,
    value_label: str,
    color: str,
    figure_height: float,
    percentage_axis: bool = False,
) -> None:
    ordered_dataframe = dataframe.sort_values(value_column, ascending=True).copy()
    figure, axis = plot.subplots(figsize=(11, figure_height), constrained_layout=True)
    statistical_graphics.barplot(
        data=ordered_dataframe,
        x=value_column,
        y=category_column,
        color=color,
        ax=axis,
    )
    axis.set_title(title, loc="left", fontsize=15, fontweight="bold")
    axis.set_xlabel(value_label)
    axis.set_ylabel("")
    if percentage_axis:
        axis.set_xlim(0, max(105, float(numerical.ceil(ordered_dataframe[value_column].max() / 10) * 10)))
    for bar in axis.patches:
        bar_value = bar.get_width()
        if percentage_axis:
            decimal_places = 2 if 0 < bar_value < 1 else 1
            bar_label = f"{bar_value:.{decimal_places}f}%"
        else:
            bar_label = f"{bar_value:,.0f}"
        axis.annotate(
            bar_label,
            (bar_value, bar.get_y() + bar.get_height() / 2),
            xytext=(4, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
        )
    axis.grid(axis="x", alpha=0.2)
    axis.grid(axis="y", visible=False)
    figure.savefig(output_path, dpi=170, bbox_inches="tight")
    plot.close(figure)


def write_market_skill_chart(market_skill_table: pandas.DataFrame, output_path: Path) -> None:
    top_market_skills = (
        market_skill_table.sort_values(
            ["market_group", "job_record_count"], ascending=[True, False]
        )
        .groupby("market_group", group_keys=False)
        .head(10)
        .copy()
    )
    top_market_skills = top_market_skills.sort_values(
        ["market_group", "share_of_jobs_with_eligible_skills_percent"],
        ascending=[True, True],
    )
    figure, axis = plot.subplots(figsize=(12, 9), constrained_layout=True)
    statistical_graphics.barplot(
        data=top_market_skills,
        x="share_of_jobs_with_eligible_skills_percent",
        y="canonical_name",
        hue="market_group",
        orient="h",
        ax=axis,
    )
    axis.set_title("Top observed skills in one common-source market comparison", loc="left", fontsize=15, fontweight="bold")
    axis.set_xlabel("Share of job records with eligible skill data (%)")
    axis.set_ylabel("")
    axis.grid(axis="x", alpha=0.2)
    axis.grid(axis="y", visible=False)
    axis.legend(title="Market group", loc="lower right")
    figure.savefig(output_path, dpi=170, bbox_inches="tight")
    plot.close(figure)


def write_historical_month_chart(monthly_table: pandas.DataFrame, output_path: Path) -> None:
    plot_table = monthly_table.copy()
    figure, axis = plot.subplots(figsize=(12, 5), constrained_layout=True)
    statistical_graphics.barplot(
        data=plot_table,
        x="posting_month",
        y="job_record_count",
        color="#177E89",
        ax=axis,
    )
    axis.set_title("International-source job records by posting month, 2023", loc="left", fontsize=15, fontweight="bold")
    axis.set_xlabel("Source posting month")
    axis.set_ylabel("Job-ad records")
    axis.tick_params(axis="x", rotation=35)
    axis.grid(axis="y", alpha=0.2)
    axis.grid(axis="x", visible=False)
    figure.savefig(output_path, dpi=170, bbox_inches="tight")
    plot.close(figure)


def render_report(query_results: dict[str, pandas.DataFrame], output_directory: Path) -> str:
    dataset_profile = query_results["dataset_profile"].iloc[0]
    source_coverage = query_results["source_coverage"]
    field_coverage = query_results["field_coverage"]
    top_skills = query_results["top_skills"].head(15)
    top_titles = query_results["top_exact_titles"].head(15)
    country_profile = query_results["country_profile"]
    monthly_table = query_results["historical_2023_monthly"]
    salary_feasibility = query_results["salary_feasibility"]
    model_feasibility = query_results["model_feasibility"]
    market_skill_table = query_results["arab_market_skill_demand"]
    work_mode_flags = query_results["work_mode_flags"]
    duplicate_counts = query_results["exact_duplicate_counts"]
    learning_resource_summary = query_results["learning_resource_verification"].iloc[0]
    skill_curation_coverage = query_results["skill_curation_coverage"]
    merged_arab_country_coverage = query_results["merged_arab_country_coverage"]
    role_country_distribution = query_results["role_country_distribution"]
    role_skill_demand = query_results["role_skill_demand"]
    role_country_skill_demand = query_results["role_country_skill_demand"]
    salary_role_country_coverage = query_results["salary_role_country_coverage"]

    market_population = (
        market_skill_table.groupby("market_group", as_index=False)[
            ["country_mapped_job_records", "jobs_with_eligible_skills"]
        ]
        .first()
    )
    top_market_skills = (
        market_skill_table.sort_values(
            ["market_group", "job_record_count"], ascending=[True, False]
        )
        .groupby("market_group", group_keys=False)
        .head(10)
    )
    mapped_country_denominators = (
        role_country_distribution.drop_duplicates(["role_id", "source_dataset"])
        .groupby("role_id")["country_mapped_role_source_records"]
        .sum()
    )
    role_country_all_sources = (
        role_country_distribution.groupby(
            ["role_rank", "role_id", "display_title", "country_key", "country_or_territory_label"],
            as_index=False,
        )
        .agg(
            role_record_count=("role_record_count", "first"),
            role_country_job_record_count=("role_country_job_record_count", "sum"),
            role_country_records_with_eligible_skills=("role_country_records_with_eligible_skills", "sum"),
            role_country_source_dataset_count=("source_dataset", "nunique"),
        )
    )
    role_country_all_sources["country_mapped_role_records"] = role_country_all_sources["role_id"].map(
        mapped_country_denominators
    )
    role_country_all_sources["share_of_country_mapped_role_records_percent"] = (
        100.0
        * role_country_all_sources["role_country_job_record_count"]
        / role_country_all_sources["country_mapped_role_records"]
    ).round(2)
    role_country_all_sources["role_country_skill_coverage_percent"] = (
        100.0
        * role_country_all_sources["role_country_records_with_eligible_skills"]
        / role_country_all_sources["role_country_job_record_count"]
    ).round(2)
    role_country_all_sources = role_country_all_sources.sort_values(
        ["role_rank", "role_country_job_record_count", "country_key"],
        ascending=[True, False, True],
    )
    role_country_all_sources["country_rank"] = (
        role_country_all_sources.groupby("role_id").cumcount() + 1
    )
    role_country_display = role_country_all_sources.loc[
        (role_country_all_sources["role_rank"] <= 5)
        & (role_country_all_sources["country_rank"] <= 3)
    ]
    role_skill_display = role_skill_demand.loc[
        (role_skill_demand["role_rank"] <= 5) & (role_skill_demand["skill_rank"] <= 5)
    ]
    role_country_skill_display = role_country_skill_demand.loc[
        (role_country_skill_demand["role_rank"] <= 5)
        & (role_country_skill_demand["country_rank"] <= 2)
        & (role_country_skill_demand["skill_rank"] <= 3)
    ]
    salary_role_country_top = salary_role_country_coverage.sort_values(
        ["records_with_any_salary_field", "records_with_explicit_currency"],
        ascending=[False, False],
    ).head(15)
    salary_role_country_currency = (
        salary_role_country_coverage.loc[
            salary_role_country_coverage["records_with_explicit_currency"] > 0
        ]
        .sort_values(
            ["records_with_explicit_currency", "records_with_any_salary_field"],
            ascending=[False, False],
        )
        .head(15)
    )
    source_summary = source_coverage[["source_dataset", "snapshot_type", "job_records"]].copy()
    source_summary["archive_share_percent"] = (100.0 * source_summary["job_records"] / int(dataset_profile["total_job_records"])).round(2)
    field_summary = field_coverage[["field_name", "present_count", "job_record_count", "present_percent"]]
    duplicate_summary = duplicate_counts[["source_dataset", "total_job_records", "exact_duplicate_rows_retained"]]
    model_summary = model_feasibility[
        [
            "source_dataset",
            "job_record_count",
            "category_label_count",
            "distinct_category_label_count",
            "title_count",
            "description_count",
            "annual_salary_field_count",
            "hourly_salary_field_count",
            "currency_count",
            "pay_basis_count",
        ]
    ]

    total_job_records = int(dataset_profile["total_job_records"])
    eligible_skill_associations = int(dataset_profile["eligible_job_skill_links"])
    eligible_distinct_skills = int(dataset_profile["eligible_distinct_skills"])
    total_skill_assignments = int(skill_curation_coverage["job_skill_assignment_count"].sum())
    reviewed_skill_rows = skill_curation_coverage.loc[
        skill_curation_coverage["analysis_decision"] == "included_reviewed"
    ]
    unreviewed_exact_only_rows = skill_curation_coverage.loc[
        skill_curation_coverage["analysis_decision"] == "excluded_needs_review"
    ]
    owner_review_rows = skill_curation_coverage.loc[
        skill_curation_coverage["analysis_decision"] == "excluded_owner_review"
    ]
    other_excluded_rows = skill_curation_coverage.loc[
        skill_curation_coverage["analysis_decision"] == "excluded_policy_or_status_mismatch"
    ]
    reviewed_canonical_skill_count = int(reviewed_skill_rows["distinct_skill_count"].sum())
    unreviewed_exact_only_skill_count = int(unreviewed_exact_only_rows["distinct_skill_count"].sum())
    owner_review_skill_count = int(owner_review_rows["distinct_skill_count"].sum())
    other_excluded_skill_count = int(other_excluded_rows["distinct_skill_count"].sum())
    unreviewed_exact_only_assignment_count = int(unreviewed_exact_only_rows["job_skill_assignment_count"].sum())
    owner_review_assignment_count = int(owner_review_rows["job_skill_assignment_count"].sum())
    other_excluded_assignment_count = int(other_excluded_rows["job_skill_assignment_count"].sum())
    if reviewed_canonical_skill_count != eligible_distinct_skills:
        raise RuntimeError("Dataset-profile and skill-review queries disagree on eligible canonical skill count.")
    if total_skill_assignments != (
        eligible_skill_associations
        + unreviewed_exact_only_assignment_count
        + owner_review_assignment_count
        + other_excluded_assignment_count
    ):
        raise RuntimeError("Skill-curation query did not account for every stored job-skill assignment.")
    jobs_with_eligible_skills = int(dataset_profile["jobs_with_eligible_skills"])
    exact_normalized_title_count = int(dataset_profile["exact_normalized_title_count"])
    exact_duplicate_rows_retained = int(dataset_profile["exact_duplicate_rows_retained"])
    country_territory_label_count = int(dataset_profile["distinct_country_territory_labels"])
    historical_2023_record_count = int(monthly_table["job_record_count"].sum())
    country_mapped_job_records = int(country_profile["job_record_count"].sum())
    market_comparison_job_records = int(market_population["country_mapped_job_records"].sum())
    arab_population = market_population.loc[
        market_population["market_group"] == "Arab markets", "country_mapped_job_records"
    ]
    other_population = market_population.loc[
        market_population["market_group"] == "Other represented markets", "country_mapped_job_records"
    ]
    arab_record_count = int(arab_population.iloc[0]) if not arab_population.empty else 0
    other_record_count = int(other_population.iloc[0]) if not other_population.empty else 0
    arab_skill_denominator = int(
        market_population.loc[
            market_population["market_group"] == "Arab markets",
            "jobs_with_eligible_skills",
        ].iloc[0]
    )
    other_skill_denominator = int(
        market_population.loc[
            market_population["market_group"] == "Other represented markets",
            "jobs_with_eligible_skills",
        ].iloc[0]
    )
    source_url_count = int(field_coverage.loc[field_coverage["field_name"] == "source_url", "present_count"].iloc[0])
    description_count = int(field_coverage.loc[field_coverage["field_name"] == "description", "present_count"].iloc[0])
    annual_salary_count = int(field_coverage.loc[field_coverage["field_name"] == "salary_year_avg_field", "present_count"].iloc[0])
    hourly_salary_count = int(field_coverage.loc[field_coverage["field_name"] == "salary_hour_avg_field", "present_count"].iloc[0])
    salary_currency_count = int(
        salary_feasibility["currency_present_records"].sum()
        if not salary_feasibility.empty
        else 0
    )
    role_salary_records_with_country = int(
        salary_role_country_coverage["records_with_any_salary_field"].sum()
    )
    role_salary_country_pairs = int(
        salary_role_country_coverage[["normalized_title", "country_key"]]
        .drop_duplicates()
        .shape[0]
    )
    role_salary_currency_records = int(
        salary_role_country_coverage["records_with_explicit_currency"].sum()
    )
    role_salary_annual_values = int(
        salary_role_country_coverage["annual_value_field_records"].sum()
    )
    role_salary_hourly_values = int(
        salary_role_country_coverage["hourly_value_field_records"].sum()
    )
    role_salary_annual_comparison_candidates = int(
        salary_role_country_coverage["annual_values_with_currency_and_matching_period"].sum()
    )
    role_salary_hourly_comparison_candidates = int(
        salary_role_country_coverage["hourly_values_with_currency_and_matching_period"].sum()
    )
    top_role_count = int(role_country_distribution["role_id"].nunique())
    arab_market_names = sorted(
        country_profile.loc[
            country_profile["country_or_territory_label"].str.casefold().isin(ARAB_COUNTRY_NAMES),
            "country_or_territory_label",
        ].unique()
    )
    absent_arab_market_names = sorted(ARAB_COUNTRY_NAMES - {country_name.casefold() for country_name in arab_market_names})
    merged_arab_market_names = set(merged_arab_country_coverage["normalized_country_label"].astype(str))
    absent_merged_arab_market_names = sorted(ARAB_COUNTRY_NAMES - merged_arab_market_names)
    absent_archive_arab_market_labels = ", ".join(country_name.title() for country_name in absent_arab_market_names)
    absent_merged_arab_market_labels = ", ".join(country_name.title() for country_name in absent_merged_arab_market_names)
    future_resource_verification_count = int(learning_resource_summary["verification_dates_after_archive_build"])
    source_marked_free_count = int(learning_resource_summary["source_marked_free_verified"])
    archive_run_id = "full_archive_parquet_v1_20261028"
    report_directory = output_directory.resolve()
    figures_directory = report_directory / "figures"
    chart_references = {
        "source": "figures/01_source_records.png",
        "skills": "figures/02_top_skills.png",
        "monthly": "figures/03_historical_2023_monthly.png",
        "coverage": "figures/04_field_coverage.png",
        "market_skills": "figures/05_arab_other_market_skills.png",
    }

    write_bar_chart(
        source_summary,
        figures_directory / "01_source_records.png",
        "source_dataset",
        "archive_share_percent",
        "Share of full-archive job-ad records by source",
        "Share of archive records (%)",
        "#177E89",
        5.8,
        percentage_axis=True,
    )
    write_bar_chart(
        top_skills.head(10),
        figures_directory / "02_top_skills.png",
        "canonical_name",
        "job_record_count",
        "Most frequently associated eligible skills",
        "Job-ad records mentioning the skill",
        "#287271",
        6.2,
    )
    write_historical_month_chart(monthly_table, figures_directory / "03_historical_2023_monthly.png")
    write_bar_chart(
        field_coverage.sort_values("present_percent", ascending=True),
        figures_directory / "04_field_coverage.png",
        "field_name",
        "present_percent",
        "Field coverage across the full archive",
        "Records with field (%)",
        "#557A95",
        7.5,
        percentage_axis=True,
    )
    write_market_skill_chart(market_skill_table, figures_directory / "05_arab_other_market_skills.png")

    top_skill_names = ", ".join(top_skills["canonical_name"].head(5).astype(str))
    top_title_names = ", ".join(top_titles["display_title"].head(5).astype(str))
    report_sections = [
        "# Pre-Backend Data Analysis",
        "",
        f"**Database:** local SQLite, imported archive `{archive_run_id}`.  ",
        "**Inputs:** read-only queries against the local SQLite snapshot; no source files or database rows were changed by this report.  ",
        "**Unit of analysis:** one retained source job-ad record unless a section explicitly counts skill associations.",
        "",
        "## Executive findings",
        "",
        f"- The archive retains **{total_job_records:,} job-ad records** and **{total_skill_assignments:,} job-skill assignments**. The reviewed analysis includes **{eligible_skill_associations:,} assignments** across **{eligible_distinct_skills:,} reviewed canonical skill IDs**; it excludes **{unreviewed_exact_only_assignment_count:,} exact-only assignments** from {unreviewed_exact_only_skill_count:,} terms awaiting review, **{owner_review_assignment_count:,} ambiguous assignments** from {owner_review_skill_count} terms awaiting owner review, and **{other_excluded_assignment_count:,} assignments** with other policy/status mismatches.",
        f"- **{jobs_with_eligible_skills:,} records** have at least one reviewed eligible skill association. The leading observed skills are {top_skill_names}.",
        f"- The exact normalized-title rule (`lower(trim(title))`) yields **{exact_normalized_title_count:,} distinct title strings**. The leading strings are {top_title_names}; titles are not yet a reviewed job-family taxonomy.",
        f"- There are **{country_territory_label_count:,} distinct supplied country/territory labels** after excluding blank and non-geographic labels. The country field has {country_mapped_job_records:,} records eligible for country-group analysis; this is a set of collected source rows, not a complete country census.",
        f"- To reduce source-mix bias, the Arab/non-Arab skill comparison is restricted to `merged_tech_jobs`: **{arab_record_count:,} Arab-labelled** and **{other_record_count:,} other-market** country-mapped records ({market_comparison_job_records:,} total). Reviewed-skill denominators are **{arab_skill_denominator:,}** and **{other_skill_denominator:,}**; remaining Arab-labelled rows have no reviewed eligible skill link and are not treated as zero-skill. Across the full archive, {len(arab_market_names)}/22 configured Arab-country labels occur (absent: {absent_archive_arab_market_labels}); in `merged_tech_jobs`, only {len(merged_arab_market_names)}/22 occur (absent: {absent_merged_arab_market_labels}), not zero-opportunity claims. This is a descriptive within-source comparison, not a representative regional market estimate.",
        f"- The only approved historical monthly series in this report covers **{historical_2023_record_count:,} International-source records posted in 2023**. Mixed `updated` fields are not treated as posting dates.",
        f"- Advertisements provide source URLs for **{source_url_count:,} ({100.0 * source_url_count / total_job_records:.2f}%)** records and descriptions for **{description_count:,} ({100.0 * description_count / total_job_records:.2f}%)**. Individual-ad details therefore remain secondary.",
        f"- Salary grouping and salary regression are **not ready**: the archive has {annual_salary_count:,} annual-average and {hourly_salary_count:,} hourly-average field values; only {salary_currency_count:,} salary-bearing records carry a supplied currency in the salary-field profile, and compatible provenance/pay-period coverage is not established.",
        f"- The role×country salary audit contains {role_salary_records_with_country:,} salary-field records across {role_salary_country_pairs:,} exact-title/country pairs; {role_salary_currency_records:,} have an explicit currency, but only {role_salary_annual_comparison_candidates:,} annual and {role_salary_hourly_comparison_candidates:,} hourly values have a matching explicit currency and pay period. These rows do not support a defensible mean or median by role and country; annual/hourly/raw-text counts overlap and are shown separately.",
        f"- **{exact_duplicate_rows_retained:,} exact duplicate source rows** are retained and flagged. No cross-source deduplication is claimed. Every stored listing has unverified activity status.",

        f"- The archive contains {int(learning_resource_summary['total_learning_resources']):,} learning-resource records, with {source_marked_free_count:,} source-marked `free_verified`; however, {future_resource_verification_count:,} have `verified_on` values after the archive build date. No resource may be promoted as currently free until the course page, price, language, access conditions, and date are rechecked.",
        "",
        "## Dataset scope and source coverage",
        "",
        "The source rows are grouped into a 2023 historical set, a latest-export snapshot with unverified listing activity, and other snapshots without a consistent period. These groups are not combined into a single current-market time series.",
        "",
        markdown_table(source_summary),
        "",
        f"![Job-ad record distribution by source]({chart_references['source']})",
        "",
        "## Field coverage",
        "",
        "Percentages use all archive job-ad records as the denominator. Salary text, annual-average, and hourly-average fields overlap and must not be added together.",
        "",
        markdown_table(field_summary),
        "",
        f"![Field coverage]({chart_references['coverage']})",
        "",
        "## Skill curation and review gate",
        "",
        "The analysis checks the policy and review status on both `job_skills` and `skills`. It includes only the consistent pairs `(approved_aliases, curated)` and `(exact_only, curated_exact_only)`. An `exact_only` policy by itself is not sufficient: unreviewed exact-only terms remain in SQLite but are excluded from metrics and matching until reviewed. Ambiguous `exclude_pending_review` terms are also excluded.",
        "",
        markdown_table(skill_curation_coverage),
        "",
        "## Skill demand",
        "",
        f"The reported demand denominator is the **{jobs_with_eligible_skills:,} job records with at least one reviewed eligible skill association**. A count is distinct job records linked to a skill, not the number of repeated raw tokens. `approved_aliases` must pair with `curated`, and `exact_only` must pair with `curated_exact_only`; all pending-review terms are excluded.",
        "",
        markdown_table(
            top_skills[
                [
                    "canonical_name",
                    "job_record_count",
                    "denominator_job_records",
                    "share_of_jobs_with_eligible_skills_percent",
                    "skill_match_policy",
                    "review_status",
                ]
            ],
            15,
        ),
        "",
        f"![Top ten eligible skills]({chart_references['skills']})",
        "",
        "## Role-title evidence",
        "",
        "A role lookup may normalize case and outer whitespace and preserve punctuation. It must not silently merge semantically similar titles, levels, or abbreviations. A curated role-family taxonomy is not present in this archive.",
        "",
        markdown_table(top_titles[["display_title", "normalized_title", "job_record_count"]], 15),
        "",
        "## Role-specific country and skill evidence",
        "",
        f"The role-by-role tables cover the {top_role_count} most frequent exact normalized title strings in this archive, selected by retained source-row count. They do not define job families. The full role-country CSV is split by source dataset, with each share using country-mapped records for that exact role and source as its denominator; the compact table below pools represented sources, uses all country-mapped rows for the exact role as its denominator, and shows how many source datasets contributed. These are retained source rows, not unique vacancies. Skill counts include only eligible reviewed links, and the denominator is role records with at least one such link.",
        "",
        "### Role × country counts (top five exact titles, pooled archive)",

        "",
        markdown_table(
            role_country_display[
                [
                    "role_rank",
                    "display_title",
                    "role_record_count",
                    "country_rank",
                    "country_or_territory_label",
                    "role_country_job_record_count",
                    "country_mapped_role_records",
                    "share_of_country_mapped_role_records_percent",
                    "role_country_records_with_eligible_skills",
                    "role_country_skill_coverage_percent",
                    "role_country_source_dataset_count",
                ]
            ]
        ),
        "",
        "### Most frequent reviewed skills by exact role (top five titles)",
        "",
        markdown_table(
            role_skill_display[
                [
                    "role_rank",
                    "display_title",
                    "role_record_count",
                    "denominator_role_records_with_eligible_skills",
                    "skill_rank",
                    "skill_name",
                    "skill_job_record_count",
                    "share_of_role_records_with_eligible_skills_percent",
                    "skill_source_dataset_count",
                ]
            ]
        ),
        "",
        "### Top skills within the leading role × country pairs",
        "",
        "The CSV includes the five most represented countries for each of the 15 frequent exact titles and the top five eligible skills within each pair. The compact table below displays the first five roles, their top two countries, and the top three skills. It shows the number of contributing source datasets and the denominator for skill shares; it is descriptive of the pooled archive, not a country labor-market estimate.",
        "",
        markdown_table(
            role_country_skill_display[
                [
                    "role_rank",
                    "display_title",
                    "country_rank",
                    "country_or_territory_label",
                    "role_country_job_record_count",
                    "denominator_role_country_records_with_eligible_skills",
                    "role_country_source_dataset_count",
                    "skill_rank",
                    "skill_name",
                    "skill_job_record_count",
                    "share_of_role_country_records_with_eligible_skills_percent",
                ]
            ]
        ),
        "",
        "## Country and market comparison",
        "",
        f"The 22-name Arab cohort is defined in `analysis/sql/10_arab_vs_other_market_skills.sql`. Across all sources, {len(arab_market_names)}/22 configured Arab-country labels occur (absent from the archive: {absent_archive_arab_market_labels}); only {len(merged_arab_market_names)}/22 occur in the `merged_tech_jobs` comparison source (absent there: {absent_merged_arab_market_labels}). These missing labels indicate no matching country value in this archive/source, not zero job opportunities. The Arab-versus-other skill comparison uses only `merged_tech_jobs`, the source with both cohorts, and excludes country-mapped records without reviewed eligible skills from the skill-share denominator. This controls the largest source-mix difference but does not fix unknown date semantics or other within-source bias. `Remote (Anywhere)`, `Worldwide`, `Other/Unknown`, blank, and NULL values are not treated as countries. The raw archive has no standard ISO country codes; a country map must be gated on reviewed name-to-geometry mapping and must provide a table/list alternative.",
        "",
        "Top supplied country/territory labels:",
        "",
        markdown_table(country_profile[["country_or_territory_label", "job_record_count"]].head(15)),
        "",
        "Arab-country labels actually represented in the comparison source:",
        "",
        markdown_table(merged_arab_country_coverage[["country_or_territory_label", "job_record_count"]]),
        "",
        "The skills below are shown as within-group shares, with counts and denominators. Both groups come from `merged_tech_jobs`; its snapshot period and listing activity are still unverified, so results describe only that collected source snapshot and do not generalize to current Arab or global job markets.",
        "",
        markdown_table(
            top_market_skills[
                [
                    "market_group",
                    "canonical_name",
                    "job_record_count",
                    "jobs_with_eligible_skills",
                    "share_of_jobs_with_eligible_skills_percent",
                ]
            ],
            20,
        ),
        "",
        f"![Arab and other represented-market skill shares]({chart_references['market_skills']})",
        "",
        "## Historical date evidence",
        "",
        f"Only the `international_jobs` source is used here. Its explicit `posted_at` values fall in 2023 and account for {historical_2023_record_count:,} rows. The chart is a historical source-snapshot distribution; it is not a current or forward-looking hiring trend.",
        "",
        markdown_table(monthly_table),
        "",
        f"![Monthly International-source postings in 2023]({chart_references['monthly']})",
        "",
        "## Salary and other model feasibility findings",
        "",
        "Salary fields are preserved as source values. Annual and hourly values are not combined. No conversion, imputation, or assumption that an estimate is an employer offer is applied. A salary chart or salary regression must remain disabled until a comparable, sufficiently sized set has a known currency, pay period, provenance, and defensible target definition.",
        "",
        markdown_table(
            salary_feasibility[
                [
                    "source_dataset",
                    "salary_provenance_status",
                    "salary_currency",
                    "salary_basis",
                    "salary_rate",
                    "records_with_any_salary_field",
                    "salary_text_records",
                    "annual_value_records",
                    "hourly_value_records",
                    "currency_present_records",
                    "basis_present_records",
                ]
            ],
            30,
        ),
        "",
        "### Salary fields by exact role and country",
        "",
        f"The role×country audit is restricted to rows with a non-empty exact title and a geographic country label. It contains {role_salary_records_with_country:,} salary-field records in {role_salary_country_pairs:,} normalized-title/country pairs; {role_salary_currency_records:,} records provide a currency, {role_salary_annual_values:,} have an annual-value field, and {role_salary_hourly_values:,} have an hourly-value field. These field counts can overlap. There are {role_salary_annual_comparison_candidates:,} annual and {role_salary_hourly_comparison_candidates:,} hourly values on the same records as both an explicit currency and matching pay-period fields. Because those comparable-amount candidate counts are zero, no mean or median is computed by role and country.",
        "",
        "Largest role/source/country salary-field groups (raw-text, annual and hourly fields remain separate):",
        "",
        markdown_table(
            salary_role_country_top[
                [
                    "source_dataset",
                    "display_title",
                    "country_or_territory_label",
                    "salary_currency",
                    "salary_basis",
                    "salary_rate",
                    "records_with_any_salary_field",
                    "salary_raw_text_records",
                    "annual_value_field_records",
                    "hourly_value_field_records",
                    "records_with_explicit_currency",
                ]
            ]
        ),
        "",
        "Currency-bearing role/source/country groups (the source basis is preserved, not converted):",
        "",
        markdown_table(
            salary_role_country_currency[
                [
                    "source_dataset",
                    "display_title",
                    "country_or_territory_label",
                    "salary_currency",
                    "salary_basis",
                    "salary_rate",
                    "records_with_any_salary_field",
                    "records_with_explicit_currency",
                    "annual_values_with_currency_and_matching_period",
                    "hourly_values_with_currency_and_matching_period",
                ]
            ]
        ),
        "",
        "Job-family classification is not approved as a stable occupational taxonomy. A separate Naive Bayes model ranks sufficiently supported exact title strings from reviewed skill presence; its held-out evaluation and limited-scope serving status are documented in `ml/evaluation/results/ROLE_TITLE_NAIVE_BAYES_EVALUATION.md`. Salary regression remains disabled because no comparable target sample is available. Skill-vector clustering is exploratory only, not a validated occupational taxonomy.",
        "",
        markdown_table(model_summary),
        "",
        "## Learning-resource review gate",
        "",
        f"SQLite contains {int(learning_resource_summary['total_learning_resources']):,} curated resource records. The source labels {source_marked_free_count:,} as `free_verified`, but {future_resource_verification_count:,} records carry a `verified_on` value later than the archive build date (2026-10-28); the archive QA report says these values were preserved and not independently rechecked. Keep the catalogue in the local database, but treat current access/cost as unverified until each course page is checked again. Do not display a free badge or promise a working link from this snapshot alone.",
        "",
        "## Work arrangement evidence",
        "",
        "The `remote_flag` values preserve source encodings. Only explicit true-like values may be described as a source-reported remote flag after per-source validation. False-like values do not prove on-site work, and the mixed `work_mode_raw` text does not support a complete remote/hybrid/on-site classification.",
        "",
        markdown_table(work_mode_flags.head(30)),
        "",
        "## Duplicate and activity policy",
        "",
        markdown_table(duplicate_summary),
        "",
        "All rows remain in SQLite. Exact duplicate rows within a source are flagged, not deleted. Cross-source reposts have not been resolved. `listing_status` is `unknown_not_verified` for all rows, so the product must not call these jobs active, open, or still accepting applications.",
        "",
        "## Product decisions supported by this analysis",
        "",
        "1. Keep role and skill analysis as the primary product journey; make individual advertisements a secondary view because descriptions and source links are sparse.",
        "2. Use exact normalized title strings for role search until a manually reviewed role taxonomy exists.",
        "3. Count job records per canonical skill and disclose the denominator; include only `(approved_aliases, curated)` and `(exact_only, curated_exact_only)` policy/status pairs, and exclude all pending-review terms.",
        "4. Label Arab-versus-other-market shares as descriptive of the represented records; show counts, source mix, and the non-overlapping group definition.",
        "5. Restrict historical trends to the International source's explicit 2023 posting dates.",
        "6. Keep salary comparison/regression, stable job-family classification, and active-listing claims disabled; the Naive Bayes exact-title ranking is served only for limited-scope review with its evaluation and caveats visible.",
        "7. Treat map rendering as conditional on reviewed geographic-name mapping; always provide accessible counts in a text/table alternative.",
        "",
        "## Reproduction",
        "",
        "Run `python analysis/generate_pre_backend_analysis.py` from the repository root with the verified archive loaded into the local SQLite file. The driver opens SQLite read-only, executes the SQL files listed in `QUERY_FILES`, and writes only aggregate CSV, Markdown, and chart outputs.",
        "",
    ]
    return "\n".join(report_sections)


def main() -> int:
    argument_parser = argparse.ArgumentParser(
        description="Generate a reproducible pre-backend analysis from the local SQLite snapshot."
    )
    argument_parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    argument_parser.add_argument("--output-directory", type=Path, default=DEFAULT_OUTPUT_DIRECTORY)
    parsed_arguments = argument_parser.parse_args()
    database_path = parsed_arguments.database.resolve()
    output_directory = parsed_arguments.output_directory.resolve()
    figures_directory = output_directory / "figures"
    output_directory.mkdir(parents=True, exist_ok=True)
    figures_directory.mkdir(parents=True, exist_ok=True)
    statistical_graphics.set_theme(style="whitegrid", context="notebook")

    with read_only_connection(database_path) as database_connection:
        imported_archive = pandas.read_sql_query(
            "SELECT source_archive_run_id FROM import_runs WHERE run_status = 'succeeded' ORDER BY import_run_id DESC LIMIT 1",
            database_connection,
        )
        if imported_archive.empty:
            raise RuntimeError("The local SQLite file has no successful archive import run.")
        if imported_archive.iloc[0]["source_archive_run_id"] != "full_archive_parquet_v1_20261028":
            raise RuntimeError("The local SQLite file does not contain the expected full archive run.")
        query_results = run_analysis_queries(database_connection)

    save_aggregate_tables(query_results, output_directory)
    report_text = render_report(query_results, output_directory)
    report_path = output_directory / "PRE_BACKEND_ANALYSIS.md"
    report_path.write_text(report_text, encoding="utf-8")
    output_manifest = {
        "source_archive_run_id": "full_archive_parquet_v1_20261028",
        "database_path": str(database_path),
        "query_count": len(QUERY_FILES),
        "aggregate_tables": [f"{query_name}.csv" for query_name in QUERY_FILES],
        "report_path": str(report_path),
        "figure_paths": [f"figures/{figure_name}" for figure_name in sorted(path.name for path in figures_directory.glob("*.png"))],
    }
    (output_directory / "analysis_manifest.json").write_text(
        json.dumps(output_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output_manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
