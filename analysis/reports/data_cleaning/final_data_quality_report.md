# تقرير تدقيق جودة البيانات والتنظيف الكامل

- **تاريخ التدقيق:** 2026-10-28
- **مرجع المصادر:** `main@6755883a8c043592d349cace4cd84aaae81d73d0+GoogleDrive:International_Tech_Jobs_Filtered.zip`
- **النطاق:** `all_declared_sources_available`
- **البيانات المنظفة:** `data/processed/jobs_cleaned_audited.csv.gz`
- **SHA-256 للبيانات المنظفة:** `6f53340a00a17f4a6d86087a6bf6d98a4fce1a1bb79b795b6237f87fd927fd72`

## النطاق واستعادة المصادر

شمل التشغيل **7 ملفات وظائف و775,155 صفًا**، إضافةً إلى ملفات base الثلاثة المستخدمة لمراجعة إثراء المهارات فقط. احتُفظ بكل صف: **0 صف محذوف**. المصادر الخام لم تُعدّل.

ملاحظة provenance: ملف International استُعيد من ZIP في Google Drive. تاريخ تعديل Drive المسجل `2026-10-31` لاحق لتاريخ التدقيق `2026-10-28`؛ سُجل الفرق ولم يُعامل تاريخ الملف كتاريخ نشر أو جمع.

### جرد المصادر المختارة

| المصدر | الصفوف | SHA-256 (بادئة) | exact duplicates محفوظة |
|---|---:|---|---:|
| `International_Tech_Jobs_Filtered.csv` | 705,866 | `1c168e124207d289` | 80 |
| `Merged_Tech_Jobs_45k_skills_enriched_AFTER_ADDING_SKILLS.xlsx` | 45,591 | `15077471b52af54c` | 11 |
| `arab_tech_jobs_skills_enriched_AFTER_ADDING_SKILLS_439.csv` | 439 | `0ed150693d089cf1` | 0 |
| `cybersecurity_jobs_expanded_6_columns.csv` | 58 | `1edc730ab5edfebd` | 0 |
| `remote_tech_jobs_foreign_after_adding_skills.csv` | 1,075 | `75e540a3e51dd112` | 0 |
| `startup_jobs_foreign_after_adding_skills.csv` | 3,543 | `4edcf9fca5861667` | 0 |
| `tech_jobs_jooble_careerjet_AGNABY_after_adding_skills.csv` | 18,583 | `bb7f57371e7a9e8d` | 0 |

## التغطية والمفقود قبل/بعد

التغطية الكاملة لكل عمود خام موجودة في `raw_source_column_coverage.csv`, ولكل عمود نهائي وفي كل مصدر في `cleaned_column_coverage.csv`. الحقول المشتركة ملخصة أدناه؛ المفقود لا يُستبدل إلا في الأعمدة المشتقة المسموح بها، والراتب الأصلي يبقى كما ورد.

| الحقل المنطقي | المصدر | مفقود قبل | النسبة قبل | مفقود بعد | النسبة بعد | أثر النقص |
|---|---|---:|---:|---:|---:|---|
| title | `International_Tech_Jobs_Filtered.csv` | 0 | 0.0% | 0 | 0.0% | high |
| country | `International_Tech_Jobs_Filtered.csv` | 43 | 0.0061% | 43 | 0.0061% | high |
| skills | `International_Tech_Jobs_Filtered.csv` | 98,054 | 13.8913% | 98,054 | 13.8913% | high |
| salary_original_text | `International_Tech_Jobs_Filtered.csv` | 705,866 | 100.0% | 676,609 | 95.8552% | high |
| salary_any_numeric_source | `International_Tech_Jobs_Filtered.csv` | 676,609 | 95.8552% | 0 | 0.0% | high |
| publication_date | `International_Tech_Jobs_Filtered.csv` | 0 | 0.0% | 0 | 0.0% | medium |
| source_collection_date | `International_Tech_Jobs_Filtered.csv` | 705,866 | 100.0% | 705,866 | 100.0% | medium |
| title | `Merged_Tech_Jobs_45k_skills_enriched_AFTER_ADDING_SKILLS.xlsx` | 0 | 0.0% | 0 | 0.0% | high |
| country | `Merged_Tech_Jobs_45k_skills_enriched_AFTER_ADDING_SKILLS.xlsx` | 60 | 0.1316% | 96 | 0.2106% | high |
| skills | `Merged_Tech_Jobs_45k_skills_enriched_AFTER_ADDING_SKILLS.xlsx` | 0 | 0.0% | 0 | 0.0% | high |
| salary_original_text | `Merged_Tech_Jobs_45k_skills_enriched_AFTER_ADDING_SKILLS.xlsx` | 22,464 | 49.2729% | 22,464 | 49.2729% | high |
| salary_any_numeric_source | `Merged_Tech_Jobs_45k_skills_enriched_AFTER_ADDING_SKILLS.xlsx` | 22,464 | 49.2729% | 3 | 0.0066% | high |
| publication_date | `Merged_Tech_Jobs_45k_skills_enriched_AFTER_ADDING_SKILLS.xlsx` | 6,693 | 14.6805% | 6,693 | 14.6805% | medium |
| source_collection_date | `Merged_Tech_Jobs_45k_skills_enriched_AFTER_ADDING_SKILLS.xlsx` | 45,591 | 100.0% | 45,591 | 100.0% | medium |
| title | `arab_tech_jobs_skills_enriched_AFTER_ADDING_SKILLS_439.csv` | 0 | 0.0% | 0 | 0.0% | high |
| country | `arab_tech_jobs_skills_enriched_AFTER_ADDING_SKILLS_439.csv` | 1 | 0.2278% | 1 | 0.2278% | high |
| skills | `arab_tech_jobs_skills_enriched_AFTER_ADDING_SKILLS_439.csv` | 0 | 0.0% | 0 | 0.0% | high |
| salary_original_text | `arab_tech_jobs_skills_enriched_AFTER_ADDING_SKILLS_439.csv` | 387 | 88.1549% | 0 | 0.0% | high |
| salary_any_numeric_source | `arab_tech_jobs_skills_enriched_AFTER_ADDING_SKILLS_439.csv` | 0 | 0.0% | 0 | 0.0% | high |
| publication_date | `arab_tech_jobs_skills_enriched_AFTER_ADDING_SKILLS_439.csv` | 360 | 82.0046% | 360 | 82.0046% | medium |
| source_collection_date | `arab_tech_jobs_skills_enriched_AFTER_ADDING_SKILLS_439.csv` | 439 | 100.0% | 439 | 100.0% | medium |
| title | `cybersecurity_jobs_expanded_6_columns.csv` | 0 | 0.0% | 0 | 0.0% | high |
| country | `cybersecurity_jobs_expanded_6_columns.csv` | 0 | 0.0% | 0 | 0.0% | high |
| skills | `cybersecurity_jobs_expanded_6_columns.csv` | 0 | 0.0% | 0 | 0.0% | high |
| salary_original_text | `cybersecurity_jobs_expanded_6_columns.csv` | 0 | 0.0% | 0 | 0.0% | high |
| salary_any_numeric_source | `cybersecurity_jobs_expanded_6_columns.csv` | 56 | 96.5517% | 56 | 96.5517% | high |
| publication_date | `cybersecurity_jobs_expanded_6_columns.csv` | 58 | 100.0% | 58 | 100.0% | medium |
| source_collection_date | `cybersecurity_jobs_expanded_6_columns.csv` | 58 | 100.0% | 58 | 100.0% | medium |
| title | `remote_tech_jobs_foreign_after_adding_skills.csv` | 0 | 0.0% | 0 | 0.0% | high |
| country | `remote_tech_jobs_foreign_after_adding_skills.csv` | 0 | 0.0% | 0 | 0.0% | high |
| skills | `remote_tech_jobs_foreign_after_adding_skills.csv` | 0 | 0.0% | 0 | 0.0% | high |
| salary_original_text | `remote_tech_jobs_foreign_after_adding_skills.csv` | 1,025 | 95.3488% | 1,025 | 95.3488% | high |
| salary_any_numeric_source | `remote_tech_jobs_foreign_after_adding_skills.csv` | 1,025 | 95.3488% | 0 | 0.0% | high |
| publication_date | `remote_tech_jobs_foreign_after_adding_skills.csv` | 1,075 | 100.0% | 1,075 | 100.0% | medium |
| source_collection_date | `remote_tech_jobs_foreign_after_adding_skills.csv` | 1,075 | 100.0% | 1,075 | 100.0% | medium |
| title | `startup_jobs_foreign_after_adding_skills.csv` | 0 | 0.0% | 0 | 0.0% | high |
| country | `startup_jobs_foreign_after_adding_skills.csv` | 0 | 0.0% | 0 | 0.0% | high |
| skills | `startup_jobs_foreign_after_adding_skills.csv` | 0 | 0.0% | 0 | 0.0% | high |
| salary_original_text | `startup_jobs_foreign_after_adding_skills.csv` | 1,952 | 55.0946% | 1,952 | 55.0946% | high |
| salary_any_numeric_source | `startup_jobs_foreign_after_adding_skills.csv` | 1,952 | 55.0946% | 1 | 0.0282% | high |
| publication_date | `startup_jobs_foreign_after_adding_skills.csv` | 3,543 | 100.0% | 3,543 | 100.0% | medium |
| source_collection_date | `startup_jobs_foreign_after_adding_skills.csv` | 3,543 | 100.0% | 3,543 | 100.0% | medium |
| title | `tech_jobs_jooble_careerjet_AGNABY_after_adding_skills.csv` | 4 | 0.0215% | 4 | 0.0215% | high |
| country | `tech_jobs_jooble_careerjet_AGNABY_after_adding_skills.csv` | 0 | 0.0% | 0 | 0.0% | high |
| skills | `tech_jobs_jooble_careerjet_AGNABY_after_adding_skills.csv` | 0 | 0.0% | 0 | 0.0% | high |
| salary_original_text | `tech_jobs_jooble_careerjet_AGNABY_after_adding_skills.csv` | 13,340 | 71.786% | 13,340 | 71.786% | high |
| salary_any_numeric_source | `tech_jobs_jooble_careerjet_AGNABY_after_adding_skills.csv` | 13,340 | 71.786% | 0 | 0.0% | high |
| publication_date | `tech_jobs_jooble_careerjet_AGNABY_after_adding_skills.csv` | 18,583 | 100.0% | 18,583 | 100.0% | medium |
| source_collection_date | `tech_jobs_jooble_careerjet_AGNABY_after_adding_skills.csv` | 18,583 | 100.0% | 18,583 | 100.0% | medium |

- عدد أعمدة dataset النهائي: **123**؛ جرى فحص نوع كل عمود، والأنواع المخالفة: **0**.
- الحقول المنطقية قبل/بعد: **775,155 / 775,155**؛ الفارق **0**.
- تقرير الأنواع الخام يتعامل مع CSV/XLSX كنص المصدر ويحصر الأشكال الرقمية/المنطقية/التاريخية المكتشفة؛ التحويل المنطقي محصور في الأعمدة المشتقة.

## مراجعة الأنواع والتواريخ والتوحيد

- أعمدة المصدر المفحوصة: **189** سجل عمود/مصدر؛ أعمدة النتيجة المفحوصة: **123**.
- حقل وقت الجمع الصريح المكتشف: **0**. إذا لم يظهر حقل جمع، تبقى قيمة collection فارغة؛ لم تُستخدم تواريخ Drive أو modified كبديل.
- `posted_at_iso` يقرأ حقول النشر فقط. `source_updated_at_iso` مستقل، ولا يتحول إلى نشر. `source_collected_at_iso` يقرأ أعمدة الجمع/السحب الصريحة فقط.
- الدول: aliases صريحة فقط في `country_standardized`؛ النص الخام محفوظ. العنوان يبقى دلاليًا كما هو مع تطبيع المسافات و`title_key` غير حساس لحالة الأحرف فقط. لم يُدمج عنوانان متشابهان تلقائيًا.
- المواقع والمدن والمناطق الخام محفوظة؛ أضيف `location_clean` لتطبيع المسافات و`location_key` للمقارنة النصية. تصنيفات العمل/نوع التوظيف و`role_family` أعمدة مشتقة مع الاحتفاظ بالقيم الخام.
- نتائج النوع والتاريخ والتوحيد: `cleaned_column_type_audit.csv`, `raw_source_type_audit.csv`, `date_quality_audit.csv`, `country_standardization_audit.csv`, و`role_family_profile.csv`.

## التكرارات والقيم الشاذة

- exact داخل المصدر محفوظ وموسوم: **91**.
- مرشحو التطابق عبر المصادر: raw-row **0**، URL **1**، توقيع إعلان **1**؛ near duplicate **0** زوجًا.
- لم يُحذف أو يُدمج أي مرشح. جرى تخطي **478** كتل متشابهة كبيرة (>60 صفًا) في المقارنة الثنائية المكلفة؛ لم تُحذف سجلاتها، وتُذكر حدود الفحص صراحة.
- قيم الرواتب التي تخرج عن IQR أو الحدود الواسعة تبقى في الملف وتُوسم للمراجعة. جدول `annual_salary_statistics_actual.csv` يتضمن الحد الأدنى والأعلى مع العلامة، ولا يحذف أو يقص قيمة.
- كل المرشحين للتكرار في `duplicate_review_candidates.csv`؛ العلامة ليست تأكيدًا أن الإعلانات تمثل الوظيفة نفسها.

## توحيد الرواتب والتقدير الاصطناعي

- `salary_raw` و`salary_candidate_raw` و`salary_original` و`source_row_json` تحفظ أصل الراتب. القيم المحولة/السنوية أعمدة منفصلة.
- العملة الأساسية: **USD**؛ القيم السنوية النظيرة متاحة في **USD وEGP وSAR**. اختيار USD كقاعدة قرار افتراضي موثق لأن المستخدم لم يحدد قاعدة وحيدة؛ تُعرض العملات الثلاث معًا.
- معدلات التحويل مؤرخة **2026-10-28**؛ USD→EGP = **56.129**، USD→SAR = **3.75**. التحويل من العملات الأخرى إلى USD موثق لكل عملة في `salary_fx_rates_used.csv` و`data/reference/fx_rates_2026-10-28.json`. جميع الرواتب، حتى ذات تاريخ نشر أقدم، حُولت بسعر يوم التدقيق؛ لا يوجد تعديل تضخم أو PPP.
- عوامل السنونة: الشهر ×12.0، الأسبوع ×52.0، يوم العمل ×260.0، الساعة ×2080.0؛ افتراض الساعة **40 × 52 = 2,080**. فترة غير معروفة لا تُسنون تخمينًا.
- أعداد الحالة النهائية: Actual **6,937**، Estimated **735,952**، Unverified **32,206**، Not disclosed **56**، Unparseable **4**، Missing بلا تقدير **0**.
- قِيَم راتب مفقودة أصلًا ملئت بتقدير Synthetic وموسومة Estimated: **715,390**. المصدر يبقى فارغًا في `salary_original`؛ لا تُعرض التقديرات كرواتب معلنة أو كمصادر خارجية. المنهج وعدد مراجع كل سجل والثقة في أعمدته.
- راتب أصلي مفقود لكن لم يُقدّر لعدم وجود مرجع كافٍ: **0**؛ القيم غير المفصح عنها لا تُقدّر، والنص غير القابل للتحليل لا يُستبدل.
- تغطية الراتب السنوي بعد التحويل: USD **739,484**، EGP **739,484**، SAR **739,484**.
- الرواتب الأصلية المفقودة قبل التقدير: **715,390**؛ القيم synthetic لا تدخل في إحصاءات Actual أو تدريب مرجع التقدير.
- نموذج التقدير: وسيط من Actual المصدرية المؤهلة فقط، بتدرج بلد+عنوان، بلد+عائلة دور+خبرة، بلد+عائلة، عالمي+عائلة+خبرة، عالمي+عائلة، ثم عالمي. أهلية التدريب: `salary_value_type=actual_reported` و`salary_statistics_eligible=yes`، وعملة وفترة معلنتان وقيمة سنوية USD موجبة صالحة؛ استُخدمت **3,354** سجلات في **2,395** مجموعات. الأعداد حسب المصدر/العملة والسياسة في `salary_model_and_fx_policy.json`. قيم IQR المتطرفة تبقى ولا تُحذف، والوسيط مقاوم لها؛ Q1–Q3 للمجموعة المرجعية نطاق Synthetic مرجعي لا نطاق راتب معلن.
- يظل `Actual` مبلغًا ظهر في ملف المصدر ولم يُتحقق حيًا من الإعلان. `Unverified` ليس راتبًا محققًا. التقديرات الموروثة تبقى `Estimated` لكن غير متحققة.

### ملفات الرواتب

- `salary_estimate_summary.csv` حسب البلد/العائلة/المنهج؛ `salary_fx_rates_used.csv` أسعار العملة؛ `annual_salary_statistics_actual.csv` إحصاءات الرواتب الفعلية المحولة سنويًا؛ `salary_statistics_actual.csv` الإحصاءات الأصلية حسب العملة والفترة.
- `salary_review_candidates.csv` لحالات مراجعة العملة/الفترة/المصدر/النطاق. لا تُخلط الرواتب المعلنة بالتقديرات.

## المهارات والحقول المرتبطة

- صفوف بها tokens مهارات: **677,101**؛ مجموع assignments canonical: **4,026,953**.
- التكرار داخل قائمة المهارة يُزال فقط من القائمة المشتقة؛ `skills_raw` لا يتغير. alias mapping صريح/محافظ؛ المصطلحات غير المراجعة تبقى exact-only ولا تُستبدل بمرادفات.
- الاختبارات تشمل تطابق عدد مهارات JSON مع العدّ، اتساق USD↔EGP/SAR، ترتيب حدود الراتب، عدم ترقية updated إلى posted، حالة `Estimated` ومصدرها، ومعرّفات السجلات.
- `field_consistency_checks.csv` يسجل كل فحص وعدد المخالفات. إذا ظهر أي إخفاق، يجب مراجعته قبل استهلاك الملف.

## قاعدة البيانات وإعادة التحليل

- فحص SQLite الداخلي لقراءة CSV وتجميع الرواتب: `passed`؛ 775,155 صفًا، 1,957 مجموعة راتب، 0 اختلافًا. هذا ليس مقارنة مع قاعدة المشروع المفقودة.
- مطابقة قاعدة البيانات الخارجية: `not_checked`؛ قاعدة المشروع السابقة وحزمة Parquet غير متاحتين في checkout، ولم يُمرر `--database-validation-json`.
- لا توجد مقارنة تاريخية أو تحقق لقاعدة خارجية؛ لا يُفترض أن قاعدة كاملة أُعيد بناؤها. فحص SQLite الداخلي لا يثبت أن الإعلانات نشطة أو أن حقوق إعادة التوزيع متاحة.

## سجل التغييرات والملفات الناتجة

كل تعديل فعلي على أعمدة مشتقة، وكل عملية تحويل/تقدير للراتب، لها سجل صفّي في `cleaning_change_log.csv.gz`؛ ملخص العمليات في `cleaning_change_summary.csv`. التكرارات/outliers غير المحذوفة تسجل كمرشحات مراجعة لا كتغييرات.

لإبقاء مستودع Git خفيفًا ومن دون نسخ الداتا، تُتبع نسخة هذا التقرير وملخصات الجودة الصغيرة اللازمة للدفتر فقط. ملف الوظائف المنظف، المصادر الخام، سجل التغييرات المضغوط، قوائم المراجعة الصفّية والجداول المولّدة الأخرى لا تُضاف إلى Git؛ الداتا المعتمدة موجودة في Drive، ويمكن إعادة توليد تقارير التشغيل الكاملة من السكربتات بعد استعادة المصادر.

- **actual_salary_statistics:** `analysis/reports/data_cleaning/salary_statistics_actual.csv`
- **cleaned_dataset:** `data/processed/jobs_cleaned_audited.csv.gz`
- **cleaning_notebook:** `analysis/notebooks/cleaning_data_audit.ipynb`
- **cleaning_summary:** `analysis/reports/data_cleaning/cleaning_summary.json`
- **country_profile:** `analysis/reports/data_cleaning/country_profile.csv`
- **final_report:** `analysis/reports/data_cleaning/final_data_quality_report.md`
- **legacy_salary_estimate_inventory:** `analysis/reports/data_cleaning/legacy_salary_estimate_inventory.csv`
- **quality_after:** `analysis/reports/data_cleaning/data_quality_after.json`
- **quality_before:** `analysis/reports/data_cleaning/data_quality_before.json`
- **salary_coverage_by_role_country:** `analysis/reports/data_cleaning/salary_coverage_by_role_country.csv`
- **salary_review_candidates:** `analysis/reports/data_cleaning/salary_review_candidates.csv`
- **skill_profile:** `analysis/reports/data_cleaning/skill_profile.csv`
- **source_manifest:** `analysis/reports/data_cleaning/source_manifest.csv`
- **full_cleaned_dataset:** `data/processed/jobs_cleaned_audited.csv.gz`
- **raw_source_column_coverage:** `analysis/reports/data_cleaning/raw_source_column_coverage.csv`
- **raw_source_type_audit:** `analysis/reports/data_cleaning/raw_source_type_audit.csv`
- **cleaned_column_coverage:** `analysis/reports/data_cleaning/cleaned_column_coverage.csv`
- **cleaned_column_type_audit:** `analysis/reports/data_cleaning/cleaned_column_type_audit.csv`
- **field_coverage_comparison:** `analysis/reports/data_cleaning/field_coverage_comparison.csv`
- **date_quality_audit:** `analysis/reports/data_cleaning/date_quality_audit.csv`
- **missingness_impact:** `analysis/reports/data_cleaning/missingness_impact.csv`
- **country_standardization_audit:** `analysis/reports/data_cleaning/country_standardization_audit.csv`
- **role_family_profile:** `analysis/reports/data_cleaning/role_family_profile.csv`
- **annual_salary_statistics_actual:** `analysis/reports/data_cleaning/annual_salary_statistics_actual.csv`
- **salary_estimate_summary:** `analysis/reports/data_cleaning/salary_estimate_summary.csv`
- **salary_fx_rates_used:** `analysis/reports/data_cleaning/salary_fx_rates_used.csv`
- **duplicate_review_candidates:** `analysis/reports/data_cleaning/duplicate_review_candidates.csv`
- **field_consistency_checks:** `analysis/reports/data_cleaning/field_consistency_checks.csv`
- **cleaning_change_log:** `analysis/reports/data_cleaning/cleaning_change_log.csv.gz`
- **cleaning_change_summary:** `analysis/reports/data_cleaning/cleaning_change_summary.csv`
- **salary_model_and_fx_policy:** `analysis/reports/data_cleaning/salary_model_and_fx_policy.json`

## حدود التفسير

1. كل التقديرات Synthetic/Estimated وليست قيمًا فعلية أو نصيحة مالية؛ قيمتها تتأثر بانحياز عينة الرواتب الفعلية الصغيرة/غير المتجانسة.
2. معدلات FX تاريخية على يوم التدقيق، وليست سعر صرف تاريخ نشر كل إعلان؛ لا يوجد تعديل تضخم أو كلفة معيشة/PPP.
3. يُسجل تاريخ الجمع فقط عند وجود حقل صريح؛ تاريخ الملف في Drive لا يثبت وقت جمع كل إعلان ولا يُستخدم بديلًا عنه.
4. تطابق عنوان/شركة/موقع/رابط يولد candidate فقط. لا تحذف أي صف قبل تأكيد أن الإعلان يمثل الوظيفة نفسها.
5. المصدر الحالي يضم snapshots ذات دلالات زمنية مختلفة؛ وجود السجل لا يعني أنه نشط حاليًا.
