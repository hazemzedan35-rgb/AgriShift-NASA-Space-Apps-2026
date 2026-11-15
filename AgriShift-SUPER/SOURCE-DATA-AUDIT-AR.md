# تدقيق مصادر AgriShift — نسخة التسليم

تم استخدام **ثلاثة ملفات أصلية أرفقها المستخدم**: ECOCROP الكامل، وLookup معاني الحقول، وملف التقويم الزراعي المصري. لم تتم إضافة قيم موثّقة باسم مصدر دون وجودها في الملف.

## إسناد المحاصيل

| Crop | ECOCROP taxon | EcoPortCode | Egypt crop-calendar records | Delta-specific records |
|---|---|---|---:|---:|
| wheat | *Triticum aestivum* | 2114 | 13 | 1 |
| faba | *Vicia faba* | 2146 | 8 | 2 |
| maize | *Zea mays* | 2175 | 0 | 0 |
| sunflower | *Helianthus annuus* | 1191 | 28 | 2 |
| rice | *Oryza sativa* | 1574 | 3 | 0 |
| cotton | *Gossypium barbadense* | 1158 | 0 | 0 |
| potato | *Solanum tuberosum* | 1971 | 26 | 2 |
| tomato | *Lycopersicon esculentum* | 1379 | 14 | 1 |
| onion | *Allium cepa* | 364 | 5 | 2 |
| sugarbeet | *Beta vulgaris* | 514 | 13 | 1 |
| alfalfa | *Medicago sativa* | 1428 | 0 | 0 |
| sorghum | *Sorghum bicolor* | 48747 | 3 | 0 |

**التفاصيل:** السجلات الـ113 هي نتيجة فلترة 714 سجلًا مصريًا في Excel للمحاصيل المحددة، عبر 12 منطقة مسمّاة؛ 3 محاصيل بدون أي سجل مطابق (`maize`, `cotton`, `alfalfa`). `rice` له 3 سجلات لكنها ليست كلها محددة بمنطقة، فلا تُنسب تلقائيًا للدلتا. `faba` يتطابق مع `Bean, broad green` لأن النموذج fresh-harvest، وليس `Bean, broad` الجاف.

**الحدود العلمية:** القطن يمثله **Gossypium barbadense** فقط؛ البنجر السكري يستخدم سجل **Beta vulgaris** الأوسع. EcoCrop هي قاعدة تاريخية عامة، لا تمثل ضمان إنتاج أو صلاحية للزراعة. مدد نمو FAO-56 قد تختلف عن مدد التقويم المصري.

## سجل التحقق من أصول الملفات (SHA-256)

- `EcoCrop_DB.csv` — 1622384 bytes — `4187e8846336e185c4583165211c5981855e95adfbefd897bd2bd481de48d106`
- `Ecocrop_variable_lookup.csv` — 1538 bytes — `7f09dc66ebb7c24f1e37ae23519249b18ae721941241cbfb0c01135039489487`
- `Crop_Calendar_Data_All.xlsx` — 78517 bytes — `df29517e67f32c8d5b26b01ceb13b469f5512dd5d53f5e9cabd082bb69bf7ac0`

## روابط المرجع

- https://github.com/OpenCLIM/ecocrop/blob/main/EcoCrop_DB.csv
- https://github.com/OpenCLIM/ecocrop/blob/main/Ecocrop_variable_lookup.csv
- https://cropcalendar.apps.fao.org/
- https://www.fao.org/4/x0490e/x0490e0b.htm
- https://power.larc.nasa.gov/docs/services/api/temporal/daily/
