#!/usr/bin/env python3
"""Анализ kernel-бенчмарков Palantir (Фаза 3 + доп. tier-конфиги).

Читает ВСЕ CSV `regime1_windows*.csv` и `regime2_all_slices*.csv` из
materials/kernels/ (glob), валидирует полноту/уникальность и печатает
markdown-таблицы (tier x таймлайн). Графики строятся при явном --figs DIR.

Примеры:
    python3 scripts/kernels_analysis.py
    python3 scripts/kernels_analysis.py --materials ~/.../materials/kernels
    python3 scripts/kernels_analysis.py --figs ./figs   # пишет PNG
"""

from __future__ import annotations

import argparse
import csv
import glob
import os

TIER_ORDER = [
    # базовое семейство (Фаза 2/3, 6 шт.)
    "ODESS",
    "N2_G3-2",
    "N3_G4-3-2",
    "N3_G8-4-2",
    "N4_G6-4-3-2",
    "N5_G12-6-4-3-2",
    # extra-семейство (полный top-tier, 8 шт.)
    "N1_G12",
    "N3_G12-4-3-2",
    "N3_G6-4-2",
    "N2_G6-4",
    "N3_G8-6-2",
    "N4_G12-8-4-2",
    "N3_G4-3-2-fn24",
    "N4_G4-3-2-1",
]
BASE_TIERS = TIER_ORDER[:6]
EXTRA_TIERS = TIER_ORDER[6:]

REGIME1_WINDOWS = [
    "4.19|5.4", "5.4|5.10", "5.10|5.15", "5.15|6.1", "6.1|6.2", "6.2|6.3",
    "6.3|6.4", "6.4|6.5", "6.5|6.6", "6.6|6.6.7", "6.6.7|6.6.14",
    "6.6.14|6.6.21", "6.6.21|6.6.28", "6.6.28|6.6-dup",
]
NUM_FIELDS = (
    "cdc_ratio", "total_dedup", "delta_gain", "stored_mb", "orig_mb",
    "elapsed_s", "mbps", "delta_stored", "fp_table_size", "sf_table_size",
)

DEFAULT_MATERIALS = "~/pornfolder/repos/marline-reports/materials/kernels"

R1_GLOB = "regime1_windows*.csv"
R2_GLOB = "regime2_all_slices*.csv"


def load(path):
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k in NUM_FIELDS:
            if k in r and r[k] != "":
                r[k] = float(r[k])
    return rows


def load_glob(materials, pattern):
    """Загружает все CSV, подходящие под pattern, добавляет поле _source."""
    rows = []
    paths = sorted(glob.glob(os.path.join(materials, pattern)))
    for p in paths:
        for r in load(p):
            r["_source"] = os.path.basename(p)
            rows.append(r)
    return rows, paths


def tier_order(rows):
    seen = [r["tier"] for r in rows]
    canonical = [t for t in TIER_ORDER if t in seen]
    extra = [t for t in dict.fromkeys(seen) if t not in canonical]
    return canonical + extra


def family(tier):
    if tier in EXTRA_TIERS:
        return "extra"
    if tier in BASE_TIERS:
        return "base"
    return "other"


def mean_by(rows, group_key, field):
    acc = {}
    for r in rows:
        acc.setdefault(r[group_key], []).append(r[field])
    return {k: sum(v) / len(v) for k, v in acc.items()}


def _duplicates(rows):
    seen = {}
    for r in rows:
        key = (r["case"], r["tier"])
        seen.setdefault(key, []).append(r.get("_source", "?"))
    return {k: v for k, v in seen.items() if len(v) > 1}


def _cdc_inconsistent(rows):
    by_case = {}
    for r in rows:
        by_case.setdefault(r["case"], {})[r["tier"]] = r["cdc_ratio"]
    bad = {}
    for case, per_tier in by_case.items():
        vals = set(round(v, 12) for v in per_tier.values())
        if len(vals) > 1:
            bad[case] = per_tier
    return bad


def validate(r1, r2):
    problems = []

    dups2 = _duplicates(r2)
    if dups2:
        problems.append(f"regime2: дубли (case,tier): {sorted(dups2)}")
    dups1 = _duplicates(r1)
    if dups1:
        problems.append(f"regime1: дубли (case,tier): {sorted(dups1)}")

    cases1 = [w for w in REGIME1_WINDOWS if any(r["case"] == w for r in r1)]
    tiers1 = tier_order(r1)
    exp1 = len(cases1) * len(tiers1)
    if len(r1) != exp1:
        problems.append(
            f"regime1: {len(r1)} строк, ожидалось {exp1} "
            f"({len(cases1)} окон × {len(tiers1)} tier из данных)"
        )
    seen = {(r["case"], r["tier"]) for r in r1}
    for w in cases1:
        for t in tiers1:
            if (w, t) not in seen:
                problems.append(f"regime1: нет строки case={w} tier={t}")

    tiers2 = tier_order(r2)
    exp2 = len(tiers2)
    if len(r2) != exp2:
        problems.append(
            f"regime2: {len(r2)} строк, ожидалось {exp2} (tier'ов из данных)"
        )

    bad_cdc1 = _cdc_inconsistent(r1)
    for case, per_tier in bad_cdc1.items():
        problems.append(
            f"regime1: cdc_ratio зависит от tier для case={case}: {per_tier}"
        )
    bad_cdc2 = _cdc_inconsistent(r2)
    for case, per_tier in bad_cdc2.items():
        problems.append(
            f"regime2: cdc_ratio зависит от tier для case={case}: {per_tier}"
        )
    return problems


def table_per_tier(rows):
    tiers = tier_order(rows)
    td = mean_by(rows, "tier", "total_dedup")
    dg = mean_by(rows, "tier", "delta_gain")
    mb = mean_by(rows, "tier", "mbps")
    st = mean_by(rows, "tier", "stored_mb")
    fp = mean_by(rows, "tier", "fp_table_size")
    sf = mean_by(rows, "tier", "sf_table_size")
    out = ["| tier | family | total_dedup | delta_gain | mbps | stored_mb | fp_table_size | sf_table_size |",
           "|---|---|---|---|---|---|---|---|"]
    for t in tiers:
        out.append(
            f"| {t} | {family(t)} | {td[t]:.4f} | {dg[t]:.4f} | {mb[t]:.1f} | {st[t]:.1f} | "
            f"{fp[t]:.0f} | {sf[t]:.0f} |"
        )
    return "\n".join(out)


def table_per_window(rows, metric="total_dedup", tiers_filter=None):
    cases = [w for w in REGIME1_WINDOWS if any(r["case"] == w for r in rows)]
    tiers = tier_order(rows)
    if tiers_filter is not None:
        tiers = [t for t in tiers if t in tiers_filter]
    per = {}
    for r in rows:
        per.setdefault((r["case"], r["tier"]), []).append(r[metric])
    head = "| case (timeline) | " + " | ".join(tiers) + " |"
    sep = "|" + "---|" * (len(tiers) + 1)
    out = [head, sep]
    for c in cases:
        cells = []
        for t in tiers:
            vals = per.get((c, t))
            cells.append(f"{sum(vals) / len(vals):.3f}" if vals else "nan")
        out.append(f"| {c.replace('|', chr(92) + '|')} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def regime2_summary(rows):
    order = tier_order(rows)
    rows = sorted(rows, key=lambda r: order.index(r["tier"]))
    out = ["| tier | family | cdc_ratio | total_dedup | delta_gain | mbps | stored_mb | orig_mb |",
           "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(
            f"| {r['tier']} | {family(r['tier'])} | {r['cdc_ratio']:.4f} | {r['total_dedup']:.4f} | "
            f"{r['delta_gain']:.4f} | {r['mbps']:.1f} | {r['stored_mb']:.1f} | {r['orig_mb']:.1f} |"
        )
    return "\n".join(out)


def build_figs(r1, r2, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(out_dir, exist_ok=True)

    def save(fig, name):
        path = os.path.join(out_dir, name)
        fig.savefig(path, dpi=140, bbox_inches="tight")
        plt.close(fig)
        return path

    def series(rows, tier, cases, field):
        by = {r["case"]: r for r in rows if r["tier"] == tier}
        return [by[c][field] if c in by else float("nan") for c in cases]

    tiers = tier_order(r1)
    cases = [w for w in REGIME1_WINDOWS if any(r["case"] == w for r in r1)]
    x = range(len(cases))
    def timeline(field, ylabel, title, name):
        fig, ax = plt.subplots(figsize=(14, 6))
        for t in tiers:
            ax.plot(x, series(r1, t, cases, field), marker="o", label=t)
        ax.set_xticks(list(x))
        ax.set_xticklabels(cases, rotation=45, ha="right", fontsize=8)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend(fontsize=7, ncol=2)
        ax.grid(alpha=0.3)
        save(fig, name)

    timeline(
        "total_dedup", "total_dedup",
        "Режим 1: total_dedup по окнам таймлайна (все 14 tier)", "r1_total_dedup_timeline.png",
    )
    timeline(
        "delta_gain", "delta_gain = total_dedup - cdc_ratio",
        "Режим 1: прирост Palantir над CDC по окнам (все 14 tier)", "r1_delta_gain_timeline.png",
    )

    # 3. trade-off dedup vs mbps (один график, все tier)
    fig, ax = plt.subplots(figsize=(12, 6))
    for t in tiers:
        xs = [r["mbps"] for r in r1 if r["tier"] == t]
        ys = [r["total_dedup"] for r in r1 if r["tier"] == t]
        ax.scatter(xs, ys, label=t, s=20)
    ax.set_xlabel("mbps")
    ax.set_ylabel("total_dedup")
    ax.set_title("Режим 1: trade-off dedup vs скорость (все 14 tier)")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.3)
    save(fig, "r1_dedup_vs_mbps.png")

    # 4. CDC ratio vs total_dedup (cdc одинаков для всех tier -> одна линия)
    fig, ax = plt.subplots(figsize=(14, 6))
    cdc_ys = [next(r["cdc_ratio"] for r in r1 if r["case"] == c and r["tier"] == tiers[0]) for c in cases]
    ax.plot(x, cdc_ys, marker="s", linestyle="--", color="black", label="cdc_ratio (база)")
    for t in tiers:
        ax.plot(x, series(r1, t, cases, "total_dedup"), marker="o", label=f"{t} total_dedup")
    ax.set_xticks(list(x))
    ax.set_xticklabels(cases, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("ratio")
    ax.set_title("Режим 1: cdc_ratio vs total_dedup (все 14 tier)")
    ax.legend(fontsize=6, ncol=2)
    ax.grid(alpha=0.3)
    save(fig, "r1_cdc_ratio_vs_total_dedup.png")

    # 5. Режим 1: stored_mb и размеры таблиц по tier'ам (bar)
    x_t = range(len(tiers))
    width = 0.25
    fig, ax = plt.subplots(figsize=(11, 5))
    st_mean = [sum(r["stored_mb"] for r in r1 if r["tier"] == t) / len([r for r in r1 if r["tier"] == t]) for t in tiers]
    fp_mean = [sum(r["fp_table_size"] for r in r1 if r["tier"] == t) / len([r for r in r1 if r["tier"] == t]) for t in tiers]
    sf_mean = [sum(r["sf_table_size"] for r in r1 if r["tier"] == t) / len([r for r in r1 if r["tier"] == t]) for t in tiers]
    ax.bar([i - width for i in x_t], st_mean, width=width, label="stored_mb")
    ax.bar(x_t, fp_mean, width=width, label="fp_table_size")
    ax.bar([i + width for i in x_t], sf_mean, width=width, label="sf_table_size")
    ax.set_xticks(list(x_t))
    ax.set_xticklabels(tiers, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("size (log)")
    ax.set_yscale("log")
    ax.set_title("Режим 1: размеры (stored_mb, fp/sf, log)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    save(fig, "r1_sizes_bar.png")

    # 6. Режим 2 (bar): total_dedup / delta_gain по tier'ам
    r2_sorted = sorted(r2, key=lambda rr: tiers.index(rr["tier"]) if rr["tier"] in tiers else 99)
    x_t2 = range(len(r2_sorted))
    width = 0.35
    fig, ax = plt.subplots(figsize=(11, 5))
    td2 = [rr["total_dedup"] for rr in r2_sorted]
    dg2 = [rr["delta_gain"] for rr in r2_sorted]
    ax.bar([i - width/2 for i in x_t2], td2, width=width, label="total_dedup")
    ax.bar([i + width/2 for i in x_t2], dg2, width=width, label="delta_gain")
    ax.set_xticks(list(x_t2))
    ax.set_xticklabels([rr["tier"] for rr in r2_sorted], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("ratio")
    ax.set_title("Режим 2 (all-slices, 15 версий): total_dedup / delta_gain")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    save(fig, "r2_bars.png")

    return out_dir


def main():
    ap = argparse.ArgumentParser(description="Анализ kernel-бенчмарков Palantir")
    ap.add_argument("--materials", default=os.path.expanduser(DEFAULT_MATERIALS))
    ap.add_argument("--figs", default=None, help="каталог для PNG (по умолчанию графики не строятся)")
    args = ap.parse_args()

    r1, paths1 = load_glob(args.materials, R1_GLOB)
    r2, paths2 = load_glob(args.materials, R2_GLOB)

    print(f"Режим 1 файлы: {[os.path.basename(p) for p in paths1]}")
    print(f"Режим 2 файлы: {[os.path.basename(p) for p in paths2]}")

    problems = validate(r1, r2)
    if problems:
        print("ПРОБЛЕМЫ:")
        for p in problems:
            print("  -", p)
    else:
        print(
            f"Валидация: OK (Режим 1: {len(r1)} строк, {len(tier_order(r1))} tier; "
            f"Режим 2: {len(r2)} строк, {len(tier_order(r2))} tier)"
        )

    print("\n## Режим 1: сводка по tier (усреднение по окнам)\n")
    print(table_per_tier(r1))
    print("\n## Режим 1: total_dedup по окнам таймлайна (tier x окно)\n")
    print(table_per_window(r1, "total_dedup"))
    print("\n## Режим 1: delta_gain по окнам таймлайна\n")
    print(table_per_window(r1, "delta_gain"))
    print("\n## Режим 2: единый срез (15 версий, 1 таймлайн)\n")
    print(regime2_summary(r2))

    if args.figs:
        build_figs(r1, r2, args.figs)
        print(f"\nГрафики записаны в {args.figs}")


if __name__ == "__main__":
    main()
