# Источники

Собрание основных статей, книг и ссылок по теме **«Интеграция и развитие подхода Palantir в системе Marline»** (см. [аннотацию](annotation.md)).

Документ ведётся в структурированной форме: по каждому материалу указываются выходные данные, ссылка, краткий *обзор* (сгенерированная выжимка, требует проверки по первоисточнику) и *зачем это нужно в работе* — пара предложений о роли материала.

> Пометка: обзоры ниже носят вспомогательный характер и сгенерированы автоматически по аннотациям/текстам. Перед цитированием сверяйтесь с оригиналом. Ссылки на PDF по возможности приведены в открытом доступе.

## Оглавление

- [1. Ядро темы: Palantir и Odess](#1-ядро-темы-palantir-и-odess)
- [2. Кодовая база: Marline и ChunkFS](#2-кодовая-база-marline-и-chunkfs)
- [3. Данные и стенды для бенчмарков](#3-данные-и-стенды-для-бенчмарков)
- [Шаблон для нового источника](#шаблон-для-нового-источника)

---

## 1. Ядро темы: Palantir и Odess

### Palantir (ASPLOS 2024)

- **Тип:** статья (конференция)
- **Авторы:** Hongming Huang, Peng Wang, Qiang Su, Hong Xu, Chun Jason Xue, André Brinkmann
- **Выходные данные:** ASPLOS '24, Proceedings of the 29th ACM International Conference on Architectural Support for Programming Languages and Operating Systems, Vol. 2, pp. 830–845, 2024.
- **Ссылки:**
  - DOI: [10.1145/3620665.3640353](https://doi.org/10.1145/3620665.3640353)
  - PDF: [henryhxu.github.io/share/hongming-asplos24.pdf](https://henryhxu.github.io/share/hongming-asplos24.pdf)
- **Обзор:** Работа развивает идеи Odess для post-deduplication delta compression. Вводит иерархию супер-признаков (тиров) с разной чувствительностью: высокий тир отбирает очень похожие блоки, низкие — расширяют покрытие. Дополнительно предложен фильтр ложных срабатываний (по compressibility дельта-блока) и менеджер жизненного цикла метаданных, снижающий накладные расходы на хранение признаков за счёт временной локальности бэкап-потоков. Итог: +7.3% к общему коэффициенту сжатия над N-Transform и Odess, +26.5% над Finesse, потеря пропускной способности в пределах 7.7%.
- **Зачем в работе:** Это базовый метод, который переносится и модифицируется в Marline — целевой объект интеграции. Именно жёстко фиксированную структуру тиров и суперфич предстоит сделать гибко настраиваемой.

### Odess (ICDE 2021 / ACM TOS 2023)

- **Тип:** статья (конференция) + расширенная журнальная версия
- **Авторы:** Xiangyu Zou, Cai Deng, Wen Xia, Philip Shilane, Haoliang Tan, Haijun Zhang, Xuan Wang
- **Выходные данные:** ICDE 2021, pp. 480–491, IEEE; расширенная версия — ACM Transactions on Storage (TOS), 2023.
- **Ссылки:**
  - DOI (extended, TOS): [10.1145/3584663](https://doi.org/10.1145/3584663)
  - IEEE Xplore (ICDE): [ieeexplore.ieee.org/document/9458911](https://ieeexplore.ieee.org/document/9458911)
- **Обзор:** Предлагает быстрый метод определения схожести: Subwindow-based Parallel Rolling (SWPR) хеширование на SIMD и Content-Defined Sampling, генерирующий компактный proxy-набор вместо обработки всех rolling hash значений. За счёт этого признаки генерируются примерно в 31.4× быстрее N-Transform при сопоставимой точности. Фактически переходный мост между классическим super-feature подходом и Palantir.
- **Зачем в работе:** Прямой предшественник Palantir и источник базовых механизмов (Gear-хеш, эскизы, super-feature). В Marline уже есть `OdessHasher`, поэтому данная работа — точка отсчёта для сравнения и для понимания, что именно добавляет иерархия тиров.

---

## 2. Кодовая база: Marline и ChunkFS

### Marline

- **Тип:** кодовая база (Rust)
- **Ссылки:**
  - Форк (рабочий): [github.com/Maxllon/marline](https://github.com/Maxllon/marline)
  - Upstream: [github.com/admitrievtsev/marline](https://github.com/admitrievtsev/marline)
- **Обзор:** Библиотека Similarity-Based Chunking поверх [ChunkFS](https://github.com/Piletskii-Oleg/chunkfs). Содержит крейты `marline_scrub` (энкодеры/декодеры, кластеризация, scrubber), `marline_sketcher` (`AronovichHasher`, `OdessHasher`), `marline_delta`. Уже есть `GdeltaEncoder`, `XdeltaEncoder`, `ZdeltaEncoder`, `LevenshteinEncoder`, `GraphClusterer`, `EqClusterer`.
- **Зачем в работе:** Это объект интеграции — сюда добавляется расширенная реализация Palantir с гибкой иерархией тиров и суперфич. Все эксперименты выполняются на этой кодовой базе.

### ChunkFS

- **Тип:** кодовая база/библиотека (Rust)
- **Ссылки:**
  - GitHub: [github.com/Piletskii-Oleg/chunkfs](https://github.com/Piletskii-Oleg/chunkfs)
  - crates.io: [crates.io/crates/chunkfs](https://crates.io/crates/chunkfs)
  - Документация: [docs.rs/chunkfs](https://docs.rs/chunkfs)
- **Обзор:** In-memory файловая система для сравнения алгоритмов дедупликации: взаимозаменяемые CDC-чейнкеры, хешеры, хранилища и методы оптимизации (FBC, SBC). Даёт единый стенд и метрики.
- **Зачем в работе:** Базовый фреймворк Marline; понимание его интерфейсов (`Chunker`, `Scrubber`, `Database`) необходимо для корректной интеграции Palantir.

---

## 3. Данные и стенды для бенчмарков

- **Тип:** датасеты/ссылки
- **Linux kernel source:** [git.kernel.org](https://git.kernel.org/) — разные версии ядра как набор для проверки гипотезы (указано в аннотации).
- **Publicly available backup-style datasets (TAR, LNX, WEB, VMA, CHM):** используются в Gdelta/Odess/Finesse; см. репозитории соответствующих работ и [Destor](https://github.com/fomy/destor).
- **File & Storage Systems Trace Repository:** [tracer.filesystems.org](https://tracer.filesystems.org/) — архив публичных трейсов реальных рабочих нагрузок (в т.ч. Alibaba Cloud, Kuaishou CSV) для бенчмарков файловых и storage-систем.
- **Обзор:** Наборы реальных нагрузок (tar-архивы исходников, снапшоты веб-сайтов, виртуальные машины, БД) с разной степенью локальности и схожести.
- **Зачем в работе:** Нужны для проверки зависимости коэффициента сжатия и производительности от конфигурации тиров на разных классах данных.

---

## Шаблон для нового источника

```markdown
### Название

- **Тип:** статья / книга / инструмент
- **Авторы:** …
- **Выходные данные:** …
- **Ссылки:** DOI/URL/PDF
- **Обзор:** 3–5 предложений: задача, метод, ключевые результаты.
- **Зачем в работе:** 1–2 предложения о роли в задаче.
```
