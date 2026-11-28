# Job-family label-quality audit — non-blocking NO-GO

**Audit decision:** NO_GO for label provenance only; it is not a training or prediction gate. The report uses the SQLite database reconstructed from only the 11 authorized NADA parts.

## Why the label-quality audit flags risks

- The database has no label-review/provenance field to identify a human-reviewed training set.
- Some source-category classes have fewer than 50 examples; rare labels cannot support reliable held-out evaluation.
- The populated role_family field is a derived label and is not marked as independently reviewed in this database.

## Label inventory

- Total advertisements: **775,155**
- Derived role_family labels: **775,155** across **16** classes. The database has no human-review/provenance field for these labels, so the count alone is not evidence of a reviewed ground truth.
- Source category_raw labels: **30,333** (**3.9132%** coverage) across **25** values.
- Review/provenance columns available: **none**.
- Smallest source-category class: **1** examples.

### Existing derived role_family counts

| Label | Records |
|---|---:|
| data_engineering | 218,452 |
| data_analytics_bi | 182,545 |
| data_science_ai_ml | 168,319 |
| other_technology | 109,557 |
| engineering_other | 41,360 |
| software_engineering | 28,507 |
| cloud_devops_platform | 11,558 |
| cybersecurity | 5,132 |
| qa_testing | 2,727 |
| network_it_support | 1,750 |
| hardware_embedded_iot | 1,743 |
| business_systems_analysis | 1,131 |
| product_management | 910 |
| project_program_management | 779 |
| sales_marketing | 579 |
| ux_ui_design | 106 |

### Source category counts

| Source category | Records |
|---|---:|
| software | 22,245 |
| hardware | 5,157 |
| cybersecurity | 2,492 |
| تكنولوجيا المعلومات | 59 |
| Other | 55 |
| Software / General Dev | 54 |
| فنيين وحرفيين | 52 |
| هندسة | 25 |
| Backend | 21 |
| Full Stack | 21 |
| Data & AI | 20 |
| Product / Project | 18 |
| DevOps / Cloud / Infra | 17 |
| Sales / Marketing | 17 |
| Mobile | 16 |
| Design / UX | 13 |
| QA / Testing | 13 |
| Frontend | 12 |
| IT Support | 11 |
| HR / Admin / Finance | 5 |
| سيارات وميكانيك | 5 |
| Engineering (non-software) | 2 |
| Security | 1 |
| تعليم | 1 |
| خدمة عملاء | 1 |

## Model evaluation and inference

- Model: **role-family-tfidf-mnb-v1**, target **role_family**.
- Test metrics on 104,948 records: accuracy **94.1457%**, Macro-F1 **76.6955%**, weighted-F1 **94.1527%**.
- Text coverage: title on 775,151 records; description on 26,494 (3.4179% of the labeled set).
- Metrics measure agreement with stored labels, not independent human-reviewed ground truth.
- Full per-class scores and confusion matrix: `job-family-model-evaluation.json`.

The label audit is informational. The API serves predictions whenever a valid `models/job-family-model.json.gz` artifact is present; missing/corrupt model files are reported independently from label provenance.

## Non-blocking quality follow-up

1. Treat the provenance warning as an interpretation caveat; it does not prevent fitting the stored role_family labels.
2. Inspect per-class test metrics and manually review low-support/error cases in job-family-model-evaluation.json.
3. If independent human-reviewed labels become available, evaluate them separately without disabling the existing classifier.
