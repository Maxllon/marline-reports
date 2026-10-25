# Источники

Аннотированный список литературы и инструментов по теме **«Интеграция и развитие подхода Palantir в системе MarLine»**. Список намеренно ограничен работами, которые используются в обзоре; расширенная библиография не нужна. Дата обращения — 25 октября 2026 года.

## Основные работы

### Palantir

H. Huang, P. Wang, Q. Su, H. Xu, C. J. Xue, A. Brinkmann. *Palantir: Hierarchical Similarity Detection for Post-Deduplication Delta Compression.* ASPLOS, Vol. 2, pp. 830--845, 2024. DOI: [10.1145/3620665.3640353](https://doi.org/10.1145/3620665.3640353).

Основной источник по теме. Palantir развивает Odess и добавляет иерархию тиров: поиск идёт от грубого Tier-1 к точному Tier-3, что позволяет сократить число проверяемых кандидатов. Настройки по умолчанию: `N=12`, `s=[4,3,2]`, `k=[3,4,6]`, sampling rate `1/128`; Tier-1 хранит все версии, Tier-2 — 5, Tier-3 — 2. Заявлено +7.3% E2E над N-Transform/Odess, +26.5% над Finesse, +27.4% покрытия и −7.7% throughput; на Linux выигрыш около 1.1%, а оптимальный brute-force на DB_Stock на 17.8% лучше Palantir. Публичная реализация в статье не указана.

### Odess

W. Xia, L. Pu, X. Zou, P. Shilane, S. Li, H. Zhang, X. Wang. *The Design of Fast and Lightweight Resemblance Detection for Efficient Post-Deduplication Delta Compression.* ACM Transactions on Storage, 19(3):1--30, 2023. DOI: [10.1145/3584663](https://doi.org/10.1145/3584663). Ранняя версия: X. Zou et al., IEEE ICDE, pp. 480--491, 2021, DOI: [10.1109/ICDE51399.2021.00048](https://doi.org/10.1109/ICDE51399.2021.00048).

Odess использует SWPR на SIMD и content-defined sampling: преобразования выполняются только над компактным proxy-набором хешей. Заявлено ускорение генерации признаков в 31.4 раза относительно N-Transform и в 7.9 раза относительно Finesse; E2E throughput выше в 3.20 и 1.41 раза. Это baseline для сравнения с Palantir; главное ограничение — один фиксированный порог похожести.

### N-Transform и Finesse

P. Shilane, M. Huang, G. Wallace, W. Hsu. *WAN-optimized Replication of Backup Datasets Using Stream-informed Delta Compression.* ACM Transactions on Storage, 8(4):1--26, 2012. DOI: [10.1145/2385603.2385606](https://doi.org/10.1145/2385603.2385606).

Y. Zhang, W. Xia, D. Feng, H. Jiang, Y. Hua, Q. Wang. *Finesse: Fine-Grained Feature Locality based Fast Resemblance Detection for Post-Deduplication Delta Compression.* USENIX FAST, pp. 121--128, 2019. [PDF](https://www.usenix.org/system/files/fast19-zhang.pdf).

Работа Shilane et al. описывает N-Transform: $N$ линейных преобразований rolling hash, глобальные минимумы и группировку в суперфичи. Параметры $(k,s)$ фиксированы, а $N$ должно делиться на $k$; маленькое $s$ даёт точность, большое — покрытие. Finesse отказывается от преобразований и использует локальные признаки подчанков, ускоряя вычисление сходства в 3.2--3.5 раза и повышая throughput на 41--85%.

### Delta-кодирование

H. Tan, W. Xia, X. Zou, C. Deng, Q. Liao, Z. Gu. *The Design of Fast Delta Encoding for Delta Compression Based Storage Systems.* ACM Transactions on Storage, 20(4):1--30, 2024. DOI: [10.1145/3664817](https://doi.org/10.1145/3664817).

Gdelta использует Gear hash, sampling index и пакетное сжатие остатка. По сравнению с Xdelta и Zdelta ускоряет кодирование и декодирование в 3.5--25 раз при росте коэффициента на 10--240%. В MarLine Gdelta уже реализован; для корректного сравнения конфигураций тиров кодер нужно зафиксировать.

## Новые направления

F. Yang, B. Mao, Y. Liu, L. Bao, W. Jiang, D. Zhang, C. Li, K. Zhou. *Achieving Better Benefits via Flexible Feature Matching in Post-Deduplication Delta Compression.* IEEE IPDPS, pp. 998--1010, 2025. DOI: [10.1109/IPDPS64566.2025.00093](https://doi.org/10.1109/IPDPS64566.2025.00093).

H. Xu, X. Zou, Y. Dong, P. Shilane, Y. Pan, C. Deng, W. Xia. *Argus: A Precise and Efficient Resemblance Detection for Post-Deduplication Delta Compression.* ACM Transactions on Storage, 22(1):1--29, 2025. DOI: [10.1145/3747839](https://doi.org/10.1145/3747839).

BePro использует гибкое сопоставление признаков (1.15--2.35 раза), Argus — bin-wise partitioning (до 1.64--2.29 раза). Это верхние ориентиры и related work, но полной настраиваемой иерархии тиров с открытой реализацией среди них нет.

## Инструменты и данные

O. Piletskii. *ChunkFS: In-memory File System for Chunking Algorithms Benchmarking.* [github.com/Piletskii-Oleg/chunkfs](https://github.com/Piletskii-Oleg/chunkfs).

In-memory стенд для сравнения CDC, хешеров и схем FBC/SBC. Ограничение — память и один узел, поэтому в экспериментах нужны окна сравнения.

A. Dmitrievtsev, M. Belimov. *MarLine: Similarity-Based Chunking Library.* [github.com/Maxllon/marline](https://github.com/Maxllon/marline).

Целевой проект. `OdessHasher` уже поддерживает `sampling_rate`, `features_num` и суперфичи, но не тиры; `SBCMap`, `SBCScrubber` и `GdeltaEncoder` переиспользуются. Публичной реализации Palantir в репозитории нет.

Linux Kernel Archives. [kernel.org](https://www.kernel.org/).

Источник Linux-датасета: 14 версий, SHA-256 из `sha256sums.asc`. Backup-данные Palantir не опубликованы, а публичные trace-наборы часто недоступны; поэтому Linux выбран первым, а backup-style данные добавляются на следующем этапе.

## Что не включено

DARE, CARD, PFC, Chunk2vec, SpeedSketch, HARD и классические Xdelta/Zdelta/VCDIFF не вынесены в отдельные записи: они либо не меняют постановку, либо упоминаются только как контекст. Это сделано, чтобы не раздувать список литературы.
