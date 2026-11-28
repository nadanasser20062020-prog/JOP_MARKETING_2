# Backend v2

باك إند مستقل جديد بـNode.js/JavaScript للتحليلات، لوحة العرض، مطابقة المهارات، وبوابة تصنيف عائلات الوظائف. لا يستورد كود الباك إند أو ML السابق. كل اتصال بقاعدة SQLite للقراءة فقط.

## التشغيل المحلي

- Node.js `22.13+` من سلسلة `22.x` (يعتمد على `node:sqlite` المدمج؛ لا يستخدم Python ولا خدمة ML خارجية).
- المسار المحلي الافتراضي للقاعدة المصدر: `../data/processed/jobs_cleaned_audited.sqlite3`. يمكن تغييره بـ`DATASET_DB_PATH`.

```bash
cd backend_v2
npm run check
npm test
npm run db:check
npm start
```

الخادم يستمع افتراضيًا على `0.0.0.0:4000`. لوحة العرض: `/` أو `/dashboard`، والـAPI: `/api/v2`. مرجع الـAPI الكامل في `API_REFERENCE.md`، ويُتاح أيضًا عبر `/api/v2/docs`.

## مصدر البيانات وإثبات المطابقة

- قاعدة SQLite التشغيلية أُعيد بناؤها من **أجزاء SQLite الـ11 المصرح بها فقط** في مجلد Drive `NADA`. لم تُستخدم أو تُفحص ملفات NADA الأخرى.
- مجلد المصدر المنظف المعتمد في Drive هو `JOP_MARKETING_2 - Cleaned Data (Audit 2026-10-28)`. يثبت manifest أن ملف CSV المضغوط المؤرخ بالتدقيق `2026-10-28` يضم `775,155` صفًا؛ ويعرض ملف التنظيف سبعة ملفات وظيفية محددة.
- أعداد `source_file` في قاعدة NADA تطابق بالاسم والعدد كلًا من الملفات السبعة في ملخص التنظيف، ومجموعها `775,155`. هذا تحقق منشأ/تغطية؛ لا ندعي أن بصمة CSV هي بصمة ملف SQLite أو أن تم إجراء مقارنة بايتية بين تمثيليهما.
- تفاصيل الأجزاء والبصمات والأعداد في `TESTING_NOTEBOOK.md`. تُستخدم أعمدة الرواتب السنوية الجديدة؛ لا يُستخدم عمود الراتب القديم الفارغ.

## بناء قاعدة النشر وVercel

```bash
# من backend_v2؛ عيّن DATASET_DB_PATH إلى SQLite المستخرجة من أجزاء NADA المعتمدة
DATASET_DB_PATH=../data/processed/jobs_cleaned_audited.sqlite3 npm run analytics:build-deploy-db
DATASET_DB_PATH=../data/processed/jobs_cleaned_audited.sqlite3 npm run ml:train-family
DATASET_DB_PATH=data/jobs_analytics.sqlite3.gz npm run db:check
npm run vercel:check
```

أمر البناء ينشئ الإسقاط المضغوط `data/jobs_analytics.sqlite3` و`data/jobs_analytics.sqlite3.gz`، ويقارن أعداد الصفوف/روابط المهارات/المهارات، وأعداد وحواصل جمع أعمدة الرواتب التسعة وحالاتها مع قاعدة المصدر، ثم يولد `reports/dashboard-data.json`. نتيجة البناء الحالي: SQLite خام **279,310,336 بايت**، وملف gzip **79,477,402 بايت**؛ `quick_check=ok` والمقارنات متطابقة. بعد بناء قاعدة النشر، `npm run ml:train-family` ينتج `models/job-family-model.json.gz` بحجم **2,437,083 بايت** وتقرير التقييم. تطبيق Vercel (`VERCEL=1`) يفك gzip قاعدة البيانات إلى مجلد مؤقت ثم يفتحها read-only، ويحمّل موديل role-family المضغوط من الأصول المضمنة. يتحقق `npm run vercel:check` من target وفئات الموديل ومن ملفات التغليف. `vercel.json` يعيد كتابة `/` و`/dashboard` إلى دالة الـAPI.

**حد نشر مهم:** ملف SQLite الخام أكبر من ميزانية دالة Vercel ذات `250 MiB`؛ لذلك يُضمَّن ملف gzip المضغوط البالغ نحو `75.8 MiB` فقط، وتحتاج البيئة المؤقتة إلى استيعاب ملف SQLite بعد فك الضغط (نحو `267 MiB`). ملف قاعدة النشر `.gitignored` وفق سياسة البيانات الحالية ولم يُرفع إلى Git أو إلى Vercel. يتضمن التغليف أيضًا موديل `role_family` المضغوط (2.44 MB) وتقرير القياس. فحص `npm run vercel:check` المحلي اجتاز الأصول السبعة بحجم **81,991,101 بايت** والتحقق من الموديل والقاعدة، لكنه لا يستبدل بناء Vercel الفعلي. إعدادات Vercel جاهزة للتغليف **عند توفير** `backend_v2/data/jobs_analytics.sqlite3.gz` قبل النشر؛ النشر الفعلي لم يُنفّذ.

| المكوّن | الغرض |
|---|---|
| `src/` | الإعدادات، قاعدة البيانات read-only، المستودع والخدمات، HTTP، لوحة HTML |
| `api/` | مدخل دالة Vercel عند اختيار `backend_v2/` جذرًا للمشروع |
| `scripts/` | فحوص الصياغة والقاعدة، بناء الإسقاط، تدقيق/تقييم ML |
| `test/` | اختبارات وحدة وتكامل بقاعدة fixture صغيرة |
| `API_REFERENCE.md` | المرجع الشامل الوحيد لكل المسارات وطريقة استخدامها |
| `TESTING_NOTEBOOK.md` | خطة ومخرجات الاختبارات لكل مرحلة |
| `BUG_REPORTS.md` | العيوب المكتشفة والإصلاحات والمخاطر المفتوحة |
| `ANALYTICS_REPORT.md` | التقرير النهائي للنتائج وتفسيرها وحدودها |
| `IMPLEMENTATION_PLAN.md` | تنفيذ العمل عبر ثلاث مراحل وبوابات اختبار |

## تدريب موديل عائلات الوظائف

التصنيف مرحلة مستقلة عن التحليلات، ويستهدف `role_family` من `title_clean` و`description_raw`. لا يستخدم `category_raw` ولا يجعل تدقيق موثوقية التسميات شرطًا للتدريب أو التنبؤ.

```bash
DATASET_DB_PATH=../data/processed/jobs_cleaned_audited.sqlite3 npm run ml:train-family
# تقييم فقط، من دون حفظ artifact:
DATASET_DB_PATH=../data/processed/jobs_cleaned_audited.sqlite3 npm run ml:evaluate-family
```

يُحفظ النموذج في `models/job-family-model.json.gz` ويُحفظ التقييم في `reports/job-family-model-evaluation.json`. خُدّمت النسخة الحالية عبر `/api/v2/ml/job-family/status` و`POST /api/v2/ml/job-family/predict`. على split الاختبار المحجوز: accuracy **94.15%** وmacro-F1 **76.70%** وweighted-F1 **94.15%**. هذه النتائج تقيس الاتفاق مع قيم `role_family` الموجودة، لا صحة مستقلة بعد مراجعة بشرية؛ التدقيق `NO_GO` باقٍ كمعلومة جودة فقط ولا يحجب الاستخدام. الوصف متاح لـ26,494 إعلانًا فقط (3.4179%) في المصدر؛ معظم أمثلة التدريب تعتمد على العنوان.

## حالة الإنجاز

التحليلات ولوحة العرض ومطابقة المهارات باقية كما هي ومختبرة. صيغت مرحلة التصنيف كإضافة منفصلة واختُبرت على fixtures وعلى كامل بيانات `role_family`. يتضمن `vercel.json` ملف النموذج والتقرير ضمن الأصول المطلوبة؛ فحص الحزمة محلي فقط، ولم يُنفّذ نشر فعلي على Vercel أو commit/push.
