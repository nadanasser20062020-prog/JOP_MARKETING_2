# JOP Marketing Intelligence API v2 — دليل الاستخدام الكامل

> هذا الملف هو مرجع الـAPI الوحيد لهذا الباك إند. يمكن فتحه محليًا من `backend_v2/API_REFERENCE.md` أو عبر `GET /api/v2/docs` بعد تشغيل الخدمة.

## 1. التشغيل ومصدر البيانات

- **Node.js:** الإصدار 22.x، من `22.13` فما فوق. يعتمد المشروع على `node:sqlite` ولا يحتاج Python أو خدمة ML خارجية.
- **محليًا:** من مجلد `backend_v2` شغّل `npm start`. المنفذ الافتراضي `4000`، والمضيف `0.0.0.0`؛ يمكن تغييره بـ`PORT` و`HOST`.
- **قاعدة المصدر المحلية:** المسار الافتراضي `../data/processed/jobs_cleaned_audited.sqlite3`؛ يمكن تغييره بـ`DATASET_DB_PATH`. الاتصال للقراءة فقط.
- **ملف النشر:** مع `VERCEL=1` يستخدم التطبيق `data/jobs_analytics.sqlite3.gz`، ويفك ضغطه إلى مجلد مؤقت عند أول اتصال ثم يفتح SQLite للقراءة فقط. يُبنى الملف المضغوط والـdashboard snapshot باستخدام `npm run analytics:build-deploy-db` بعد ضبط `DATASET_DB_PATH` على قاعدة المصدر المعتمدة.
- **نطاق المصدر:** قاعدة التشغيل أُعيد بناؤها من أجزاء قاعدة SQLite الـ11 المسموح بها وحدها في مجلد Drive `NADA`. تمت مطابقة أعداد السجلات لكل واحد من ملفات المصدر السبعة مع `cleaning_summary.json` في مجلد Drive `JOP_MARKETING_2 - Cleaned Data (Audit 2026-10-28)`؛ كما يحدد `cleaned_dataset_manifest.json` تاريخ التدقيق `2026-10-28` وعدد `775,155` صفًا وبصمة الأرشيف المنظف `6f53340a00a17f4a6d86087a6bf6d98a4fce1a1bb79b795b6237f87fd927fd72`. بصمة CSV المضغوط ليست بصمة ملف SQLite، وأجزاء CSV لم تُنزّل لإجراء مقارنة خلية بخلية؛ تحقق الأعداد/الملفات وحدوده موثقان في `TESTING_NOTEBOOK.md`.

### واجهات أساسية

| الطريقة | المسار | الغرض |
|---|---|---|
| `GET` | `/` أو `/dashboard` | لوحة العرض العربية |
| `GET` | `/health` أو `/api/v2/health` | فحص اتصال قاعدة SQLite ومخططها |
| `GET` | `/api/v2` | معلومات الإصدار وروابط الصحة والتوثيق |
| `GET` | `/api/v2/docs` | هذا المرجع بصيغة Markdown |
| `GET` | `/api/v2/analytics/overview` | إجمالي الإعلانات والوظائف والدول والملخص العام |
| `GET` | `/api/v2/analytics/dashboard` | بيانات الرسوم ولوحة العرض |
| `GET` | `/api/v2/analytics/roles` | البحث في مسميات الوظائف |
| `GET` | `/api/v2/analytics/role` | تقرير كامل لمسمى وظيفي |
| `GET` | `/api/v2/analytics/role/countries` | توزيع المسمى حسب الدول |
| `GET` | `/api/v2/analytics/role/skills` | المهارات الأكثر ظهورًا للمسمى |
| `GET` | `/api/v2/analytics/role/technology-combinations` | تراكيب المهارات المتزامنة للمسمى |
| `GET` | `/api/v2/analytics/role/salaries` | الرواتب السنوية للمسمى حسب الدولة والعملة |
| `GET` | `/api/v2/analytics/role/work-mode` | أنماط العمل للمسمى |
| `GET` | `/api/v2/analytics/skills` | المهارات الأكثر ظهورًا في كامل البيانات |
| `GET` | `/api/v2/analytics/work-mode` | توزيع أنماط العمل العام أو لمسمى محدد |
| `GET` | `/api/v2/analytics/markets/arab-vs-international` | مقارنة أعداد الإعلانات والمهارات والرواتب بين الأسواق |
| `POST` | `/api/v2/ml/skill-to-job-match` | مطابقة مهارات قابلة للتفسير |
| `GET` | `/api/v2/ml/job-family/status` | حالة موديل `role_family` وتقرير جودة الوسوم غير الحاجب |
| `POST` | `/api/v2/ml/job-family/predict` | تصنيف نص إعلان إلى إحدى فئات `role_family` |

كل المسارات تحت `/api/v2`، ما لم يُذكر خلاف ذلك. لا توجد مصادقة مدمجة حاليًا؛ أضف طبقة وصول مناسبة قبل وضع الخدمة خلف رابط عام إذا تطلب النشر ذلك.

## 2. شكل الاستجابة والأخطاء

### نجاح JSON

```json
{
  "success": true,
  "data": {},
  "meta": { "requestId": "..." }
}
```

يُرسل المعرّف نفسه في ترويسة `X-Request-Id`. يمكن للعميل تمرير `x-request-id`؛ يُقصّ إلى 80 حرفًا. استجابات التحليل الناجحة لا تضيف تفاصيل خارج `data` و`meta`.

### خطأ JSON

```json
{
  "success": false,
  "error": { "code": "BAD_REQUEST", "message": "..." },
  "meta": { "requestId": "..." }
}
```

| HTTP | أمثلة `code` | الحالة |
|---:|---|---|
| `400` | `BAD_REQUEST` | مدخلات أو JSON غير صالح |
| `404` | `NOT_FOUND` | مسمى غير موجود أو مسار غير معروف تحت `/api/v2` |
| `413` | `BODY_TOO_LARGE` | جسم الطلب تجاوز الحد الافتراضي `64 KiB` |
| `503` | `DATABASE_*`, `MODEL_NOT_BUILT`, `MODEL_ARTIFACT_INVALID` | قاعدة البيانات غير متاحة أو ملف النموذج مفقود/غير صالح |
| `500` | `INTERNAL_ERROR` أو خطأ أصلي | خطأ داخلي؛ تُخفى التفاصيل في وضع الإنتاج |

يقبل الخادم `OPTIONS` ويرد `204` مع `Allow: GET, POST, OPTIONS`. لا يفعّل CORS عامًا؛ تستخدم اللوحة مسارات same-origin.

## 3. الصحة ومعلومات الخدمة واللوحة

### `GET /api/v2/health` و`GET /health`

يفتح الاتصال للقراءة فقط، ويتحقق من المخطط المطلوب، ثم ينفّذ استعلامًا بسيطًا. لا يشغّل `quick_check` الكامل مع كل طلب.

مثال:

```json
{
  "success": true,
  "data": { "status": "ok", "database": "read-only-connected", "apiVersion": "v2" },
  "meta": { "requestId": "..." }
}
```

إذا فشل الاتصال أو فحص المخطط، تكون الاستجابة `503`.

### `GET /api/v2`

يعيد الاسم والإصدار وروابط التوثيق والصحة، ولا يتطلب فتح قاعدة البيانات:

```json
{
  "success": true,
  "data": {
    "name": "JOP Marketing Intelligence API",
    "version": "v2",
    "documentation": "/api/v2/docs",
    "health": "/api/v2/health"
  },
  "meta": { "requestId": "..." }
}
```

### `GET /api/v2/docs`

يعيد هذا الملف بترويسة `Content-Type: text/markdown; charset=utf-8`.

### `GET /`, `GET /dashboard`، و`GET /api/v2/dashboard`

تعيد واجهة HTML عربية ذات تصميم متجاوب ورسوم لأكثر المسميات والدول والمهارات، وأنماط العمل، والأسواق العربية والدولية. تحتوي على بحث يرسل طلب تقرير الدور إلى الـAPI. تُجهز Vercel المسارين `/` و`/dashboard` لإعادة الكتابة إلى `/api/v2/dashboard`.

## 4. التحليلات العامة

### `GET /api/v2/analytics/overview`

لا يحتاج معاملات. الحقول الأساسية:

- `totalJobs`: عدد الإعلانات في المقام العام.
- `distinctRoles`: عدد قيم `title_key` المميزة؛ ليس عدد العائلات المهنية.
- `distinctCountries`: عدد الدول غير الفارغة في الحقل المعياري.
- `sourceCount`: عدد مصادر البيانات.
- `topRole`: المسمى الأعلى عددًا مع `roleKey`, `title`, `advertisementCount`.
- `workModes`: أعداد أنماط العمل العامة.
- `salaryCoverage`: عدد السجلات ذات راتب سنوي مركزي لكل من USD وEGP وSAR.
- `generatedAt` و`salaryBasis`.

### `GET /api/v2/analytics/dashboard`

يعيد بيانات جاهزة للرسوم: `overview`, `topRoles`, `topCountries`, `topSkills`, `marketComparison`, `workModes`, و`charts`. يستخدم نسخة dashboard مُسبقة إذا كان رقم إصدارها يطابق metadata قاعدة النشر؛ وإذا غابت أو لم تتطابق، يحسبها من قاعدة البيانات.

تحتوي كل كائنات `charts` على نوع الرسم، والوحدة، والتسميات والقيم. يستطيع العميل رسمها بـSVG/Canvas أو مكتبة رسوم من اختياره؛ لا يعتمد الخادم على خدمة رسوم خارجية.

### `GET /api/v2/analytics/roles?q={prefix}&limit={n}`

- `q` اختياري؛ البحث بادئة في `title_key` بعد التطبيع.
- `limit` اختياري، الافتراضي `25`، والنطاق `1–100` (أو حد `MAX_API_LIMIT` المهيأ).
- يعيد `{ query, roles }`؛ كل عنصر: `roleKey`, `title`, `advertisementCount`.

مثال:

```bash
curl 'http://localhost:4000/api/v2/analytics/roles?q=data%20eng&limit=10'
```

### `GET /api/v2/analytics/skills?limit={n}`

الحد الافتراضي `25`، والنطاق `1–100`. يعيد `denominatorAdvertisements` والمهارات المرتبة، ولكل مهارة `skillId`, `skill`, `category`, `advertisementCount`, `appearancePctOfAllAds`. نسبة الظهور مقامها إجمالي الإعلانات، وليس عدد كل روابط المهارات.

### `GET /api/v2/analytics/work-mode[?title={role}]`

من دون `title` يستخدم كامل قاعدة البيانات؛ مع `title` يستخدم الدور المطبع. الحقول: `role`, `denominatorAdvertisements`, `categories`, ونسب `remotePct`, `nonRemotePct`, `hybridPct`, `unknownPct`, و`interpretation`.

القيم المعيارية هي `remote`, `not_remote_explicit`, `hybrid`, و`unknown_or_unmapped`. **`not_remote_explicit` تعني أن الإعلان لم يُصنّف صراحةً على أنه عن بُعد؛ لا تثبت حضورًا للمكتب.**

## 5. تقرير الدور وواجهاته الجزئية

### `GET /api/v2/analytics/role?title={role}`

`title` مطلوب. تتم مطابقة القيمة مع `title_key` بعد تطبيع المسافات والحروف. إذا لم يوجد المسمى تكون الاستجابة `404 NOT_FOUND`.

```bash
curl --get 'http://localhost:4000/api/v2/analytics/role' \
  --data-urlencode 'title=Data Engineer'
```

الحقول الرئيسية في `data`:

- `role`: المفتاح والعنوان المعروض.
- `advertisementCount`, `sourceCount`, `roleFamilyLabelsPresent`.
- `countryDemand`: لكل دولة `roleAdvertisements`, `totalAdvertisementsInCountry`, `roleShareOfItsAdvertisementsPct`, و`roleDemandWithinCountryPct`.
  - `roleShareOfItsAdvertisementsPct` = إعلانات الدور في الدولة ÷ كل إعلانات هذا الدور.
  - `roleDemandWithinCountryPct` = إعلانات الدور في الدولة ÷ كل إعلانات تلك الدولة.
- `mostDemandCountries`: أول 10 عناصر من توزيع الدول.
- `skills`: `skillId`, `skill`, `category`, `advertisementCount`, `appearancePctOfRoleAds`. مقام النسبة هو إجمالي إعلانات الدور.
- `technologyCombinations`: زوج مهارات ظهر في الإعلان نفسه؛ يحتوي أسماء المهارتين وعدد التزامن ونسبته من إعلانات الدور. الأزواج ليست دليلًا على ترتيب أو علاقة سببية.
- `annualSalaryByCountry`: لكل دولة عدد إعلانات الدور، وقائمة `currencies` لكل من `USD`, `EGP`, `SAR`.
- `workMode`: الفئات والنسب ومقامها وتفسير «غير عن بُعد».
- `storedFamilyLabelDistribution`: وصف لتسميات `role_family` الموجودة فقط؛ ليست تنبؤًا أو حقيقة مراجعة.
- `charts`: payloads جاهزة لرسم توزيع الدولة والمهارات والرواتب وأنماط العمل والتراكيب.

### واجهات الدور الجزئية

كلها تتطلب `?title=...` وتعيد `{ role, data }`:

| المسار | `data` |
|---|---|
| `/api/v2/analytics/role/countries` | توزيع الدول ونسب الطلب |
| `/api/v2/analytics/role/skills` | المهارات ونسب ظهورها |
| `/api/v2/analytics/role/technology-combinations` | أزواج المهارات المتزامنة |
| `/api/v2/analytics/role/salaries` | المتوسطات والمدى والتغطية لكل عملة/دولة |
| `/api/v2/analytics/role/work-mode` | أنماط العمل ونسبها |

مثال:

```bash
curl --get 'http://localhost:4000/api/v2/analytics/role/salaries' \
  --data-urlencode 'title=Data Engineer'
```

## 6. الرواتب السنوية

يستعمل الـAPI **الأعمدة السنوية الجديدة المعبأة**: `salary_annual_min_*`, `salary_annual_salary_*`, `salary_annual_max_*` للعملات USD وEGP وSAR. لا يعتمد على أعمدة الراتب الخام/القديمة ذات الخلايا الفارغة. لكل مجموعة عملة:

```json
{
  "currency": "USD",
  "period": "annual",
  "records": 9659,
  "mean": 156858.22,
  "range": { "minimum": 90000, "maximum": 156862.5 },
  "averageAdvertisedLowerBound": 128196.05,
  "averageAdvertisedUpperBound": 156860.86,
  "estimateStatusCounts": { "estimated": 9658, "actual": 1, "unverified": 0 }
}
```

- `mean`: متوسط القيمة السنوية المركزية؛ عند غياب المركز يستخدم منتصف الحدين إن وُجدا.
- `range.minimum/maximum`: أصغر حد أدنى وأكبر حد أعلى متاحان في المجموعة، مع استخدام المركز عند غياب الحد المقابل.
- `records`: السجلات ذات قيمة سنوية مركزية صالحة.
- `estimateStatusCounts`: توزيع الحالات المعروفة داخل السجلات المحتسبة. قد تختلف الحالة عن `Not disclosed` أو `Unparseable` لأن هذه السجلات لا تدخل عادةً في مقام قيمة راتب متاحة.
- كل عملة مستقلة؛ لا تجمع USD وEGP وSAR في متوسط واحد. قيم Estimated مشتقة وليست عروضًا مؤكدة أو نصيحة مالية.

## 7. مقارنة الأسواق العربية والدولية

### `GET /api/v2/analytics/markets/arab-vs-international?limit={n}`

`limit` اختياري؛ الافتراضي `15`، والنطاق `1–100`. يعيد:

- `counts`: عدد الإعلانات وعدد المسميات المميزة لكل سوق.
- `salaries`: متوسطات ومدى الرواتب السنوية لكل سوق وعملة، مع الأعداد والحالات.
- `topSkillsByMarket`: أكثر المهارات، ونسبة ظهور كل منها من إعلانات السوق نفسه.
- `topRolesByMarket`: أكثر المسميات إعلانًا.
- `marketDefinitions`, `salaryBasis`, و`charts`.

المجموعات: `arab` (قائمة الدول العربية المعيارية مع بعض مرادفات UAE/KSA)، و`international` (قيمة دولة غير عربية وغير فارغة)، و`unknown` (الموقع فارغ أو قيمة نطاق غير جغرافي مثل worldwide/remote/anywhere). لا تُجبر القيم المجهولة على إحدى المجموعتين.

## 8. مطابقة المهارات `POST /api/v2/ml/skill-to-job-match`

يرسل جسم JSON. مثال:

```bash
curl 'http://localhost:4000/api/v2/ml/skill-to-job-match' \
  -H 'content-type: application/json' \
  -d '{"skills":["Python","SQL"],"country":"Egypt","workMode":"remote","limit":5}'
```

| الحقل | النوع | الافتراضي/الحد |
|---|---|---|
| `skills` | مصفوفة أسماء أو معرّفات المهارات | مطلوب، 1–40 عنصرًا |
| `country` | نص دولة اختياري | تطابق بعد التطبيع |
| `workMode` | نص اختياري | `remote`, `hybrid`, `non_remote`, `unknown`؛ تقبل أيضًا aliases موثقة في الخدمة مثل `onsite` و`not_remote_explicit` |
| `roleFamily` | نص اختياري | مفتاح عائلة مخزن؛ يطابق بعد التطبيع |
| `limit` | عدد صحيح اختياري | `10` افتراضيًا، ويُحصر في `1–20` |

يعيد `scoringMethod`, `inputSkillCount`, `matchedCanonicalSkills`, `unknownSkills`, `ambiguousSkills`, `filters`, `advertisements`, `roleProfiles`, و`limitations`. في الإعلان المطابق تظهر `matchedSkills`, `missingSkills`, `userSkillCoveragePct`, `advertisementSkillCoveragePct`, وعدد المهارات المطلوبة/المتطابقة. الملف المهاري يعرض المهارات الشائعة المفقودة مع عدد الإعلانات.

التطابق اسم/alias معياري دقيق؛ لا يوجد fuzzy matching صامت. تظهر المهارة الغامضة مع `choices` بدل تخمينها. إذا لم تُحل أي مهارة إلى سجل معروف، تكون قوائم النتائج فارغة وتُعاد رسالة توجيهية.

**تنبيه:** نسبة التغطية تداخل وصفي قابل للتفسير، وليست احتمال توظيف ولا حكمًا شاملًا على ملاءمة الشخص. والمهارات الناقصة اقتراحات تكرار سوقي، وليست توصية تعلم شخصية.

## 9. تصنيف عائلات الوظائف (مرحلة ML مستقلة)

يستخدم مصنف Node.js فئة `role_family` المخزنة كهدف، ونص `title_clean` و`description_raw` كمدخل. الخوارزمية TF-IDF لكلمات unigram/bigram ثم Multinomial Naive Bayes؛ لا يعتمد التدريب على `category_raw` ولا على بوابة موافقة بشرية.

### التدريب والتقييم

من مجلد `backend_v2`:

```bash
DATASET_DB_PATH=../data/processed/jobs_cleaned_audited.sqlite3 npm run ml:train-family
# تقييم فقط دون حفظ ملف النموذج:
DATASET_DB_PATH=../data/processed/jobs_cleaned_audited.sqlite3 npm run ml:evaluate-family
```

التدريب يقرأ قاعدة المصدر الكاملة بوضع read-only، ويقسم مجموعات النص المتطابقة إلى train/validation/test عبر SHA-256 ثابت؛ لذلك لا تتسرب النسخ النصية المتطابقة بين الأقسام. ملف التشغيل هو `models/job-family-model.json.gz`، وتقرير القياس الكامل، بما فيه precision/recall/F1 لكل فئة ومصفوفة الالتباس، هو `reports/job-family-model-evaluation.json`.

نتيجة التدريب الحالي على 775,155 سجلًا و16 فئة: 612,197 train، و58,010 validation محفوظة، و104,948 test عبر 19,699 مجموعة نص اختبار. على مجموعة الاختبار: accuracy **94.15%**، macro-F1 **76.70%**، weighted-F1 **94.15%**. هذه المقاييس تقيس مطابقة النموذج للتسميات المخزنة فقط؛ `role_family` مشتق وغير موثق كمراجعة بشرية. دعم الفئات غير متوازن، مثل 8 سجلات اختبار فقط لفئة `ux_ui_design` (F1=0.50)، لذا لا تعني accuracy العالية صحة مستقلة أو أداءً متساويًا لكل الفئات. كما أن `description_raw` موجود في 26,494 سجلًا فقط (3.4179%)؛ يعتمد معظم التدريب فعليًا على عنوان الإعلان.

### `GET /api/v2/ml/job-family/status`

يعيد `decision` بقيمة `MODEL_READY` أو `MODEL_NOT_BUILT`، و`predictionEnabled` و`targetField` وبيانات النموذج والتقييم. يبقى تدقيق جودة الوسوم داخل `labelQualityAudit` ويظهر `NO_GO` لغياب منشأ المراجعة؛ هذا تحذير وصفي غير حاجب للتدريب أو التنبؤ. غياب ملف النموذج، لا نتيجة تدقيق الوسوم، هو ما يعطل التنبؤ.

### `POST /api/v2/ml/job-family/predict`

يرسل نصًا واحدًا، أو عنوانًا ووصفًا:

```bash
curl -X POST 'http://localhost:4000/api/v2/ml/job-family/predict' -H 'content-type: application/json' -d '{"title":"Data Engineer","description":"Build Python and SQL pipelines"}'
```

يمكن أيضًا إرسال `{ "text": "Data Engineer — Python, SQL, and data pipelines" }`. يجب ألا يتجاوز النص 16,000 محرف. مثال استجابة: `data.roleFamily`، `data.targetField` (`role_family`)، `modelVersion`، `algorithm` و`trainedAtUtc`. لا يعيد المسار احتمالًا أو confidence غير معاير. يعتمد التنبؤ على ملف النموذج فقط ولا يفتح SQLite التحليلات؛ بذلك تبقى مرحلة ML مستقلة. عند غياب artifact يعيد `503 MODEL_NOT_BUILT`، لا `409` بسبب جودة الوسوم.

## 10. سلوك التحديد والتطبيع والتخزين المؤقت

- `title` يطابق `title_key` المعياري، وليس مطابقة جزئية. استخدم `/analytics/roles?q=...` للبحث بالبادئة قبل التقرير.
- `limit` العام لا يتجاوز `MAX_API_LIMIT` (الافتراضي `100`). القيم غير الصحيحة أو الخارجة عن النطاق تُرفض بـ`400`، لا تُحوّل بصمت.
- الجسم JSON لا يتجاوز `MAX_BODY_BYTES` (الافتراضي `64 KiB`؛ حد الإعداد الأعلى `1 MiB`).
- ردود التحليلات تُخزّن مؤقتًا في الذاكرة مدة `CACHE_TTL_MS` (الافتراضي `30,000 ms`؛ حد الإعداد `300,000 ms`). كل بيئة serverless قد تملك cache مستقلة.
- يتصل التطبيق بـSQLite بوضع read-only و`query_only`. لا يكتب إلى قاعدة المصدر أو قاعدة النشر في وقت الطلب.
- يتطلب تشغيل Vercel اختيار `backend_v2/` جذرًا للمشروع وتجهيز `data/jobs_analytics.sqlite3.gz`, و`models/job-family-model.json.gz`, و`reports/job-family-model-evaluation.json`, و`reports/job-family-readiness.json`, و`reports/dashboard-data.json` قبل التغليف؛ انظر قسم النشر في `README.md` و`TESTING_NOTEBOOK.md`. لم يُنفّذ نشر فعلي إلى Vercel في هذا العمل.
