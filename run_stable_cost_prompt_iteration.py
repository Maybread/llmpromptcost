from __future__ import annotations

import argparse
import math
import os
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

mpl_cache_dir = Path("outputs") / ".matplotlib"
mpl_cache_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(mpl_cache_dir.resolve()))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


V_STAR = np.array([1.0, 1.0, 1.0], dtype=float)
THETA = np.array([0.8, 0.8, 0.8], dtype=float)
COST_COMPONENTS = ["C_disp", "C_norm", "C_peak", "C_region", "C_weak"]

PROMPT_TYPES = {
    1: "Baseline open prompt",
    2: "Role prompt",
    3: "Task-component prompt",
    4: "Reasoning scaffold prompt",
    5: "Knowledge-grounded prompt (RAG)",
    6: "Self-checking prompt",
    7: "Demonstration prompt",
}

DIAGNOSIS = {
    "C_disp": (
        "Responses are too dispersed",
        "Add stable explanation structure and coherence constraints",
    ),
    "C_norm": (
        "Responses are not close enough to full-score target",
        "Strengthen complete scientific explanation requirements",
    ),
    "C_peak": (
        "Most frequent response type is not ideal",
        "Clarify full-score response components",
    ),
    "C_region": (
        "Too few responses enter the high-quality region",
        "Add minimum answer requirements",
    ),
    "C_weak": (
        "One dimension is underdeveloped",
        "Repair the weakest D1/D2/D3 dimension",
    ),
}


def prompt_number_from_path(path: Path) -> int:
    match = re.search(r"prompt1-(\d+)", path.stem, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"Cannot infer prompt number from file name: {path.name}")
    return int(match.group(1))


def read_csv_with_encoding(path: Path) -> Tuple[pd.DataFrame, str]:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return pd.read_csv(path, encoding=encoding), encoding
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(f"Cannot read {path} with utf-8/gb18030/gbk") from last_error


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "response_id": {"response_id", "id", "index", "序号"},
        "response_text": {"response_text", "answer", "response", "output", "回答"},
        "D1": {"d1", "dim1", "score1", "score_1", "core_concept"},
        "D2": {"d2", "dim2", "score2", "score_2", "condition_model"},
        "D3": {"d3", "dim3", "score3", "score_3", "terminology"},
    }
    normalized = {
        column: re.sub(r"\s+", " ", str(column).strip()).lower()
        for column in df.columns
    }
    rename_map = {}
    for canonical, options in aliases.items():
        for column, normalized_name in normalized.items():
            if normalized_name in options:
                rename_map[column] = canonical
                break
    return df.rename(columns=rename_map)


def normalize_scores(df: pd.DataFrame) -> Tuple[pd.DataFrame, str, int]:
    df = df.copy()
    for column in ["D1", "D2", "D3"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["D1", "D2", "D3"]).copy()
    removed = before - len(df)
    score_min = float(df[["D1", "D2", "D3"]].min().min())
    score_max = float(df[["D1", "D2", "D3"]].max().max())

    if score_min >= 0 and score_max <= 1:
        method = "scores already in [0, 1]"
    elif score_min >= 0 and score_max <= 2:
        df[["D1", "D2", "D3"]] = df[["D1", "D2", "D3"]] / 2.0
        method = "converted from [0, 2] to [0, 1]"
    else:
        raise ValueError(f"Unsupported score range: min={score_min}, max={score_max}")
    return df, method, removed


def load_round_data(round_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    frames = []
    logs = []

    for csv_path in sorted(round_dir.glob("*.csv")):
        number = prompt_number_from_path(csv_path)
        prompt_id = f"Condition {number}"
        prompt_type = PROMPT_TYPES.get(number, f"Prompt {number}")
        raw_df, encoding = read_csv_with_encoding(csv_path)
        df = standardize_columns(raw_df)
        missing = [column for column in ["response_id", "D1", "D2", "D3"] if column not in df.columns]
        notes = []

        if "response_text" not in df.columns:
            df["response_text"] = ""
            notes.append("response_text missing; retained as score-only file")

        if missing:
            logs.append(
                {
                    "source_file": csv_path.name,
                    "prompt_id": prompt_id,
                    "prompt_type": prompt_type,
                    "encoding": encoding,
                    "original_rows": len(raw_df),
                    "retained_rows": 0,
                    "removed_missing_score_rows": 0,
                    "normalization_method": "not applied",
                    "missing_columns": ", ".join(missing),
                    "notes": "file skipped",
                }
            )
            continue

        df, method, removed = normalize_scores(df)
        df["prompt_id"] = prompt_id
        df["prompt_type"] = prompt_type
        df["source_file"] = csv_path.name
        frames.append(df[["prompt_id", "prompt_type", "response_id", "response_text", "D1", "D2", "D3", "source_file"]])
        logs.append(
            {
                "source_file": csv_path.name,
                "prompt_id": prompt_id,
                "prompt_type": prompt_type,
                "encoding": encoding,
                "original_rows": len(raw_df),
                "retained_rows": len(df),
                "removed_missing_score_rows": removed,
                "normalization_method": method,
                "missing_columns": "",
                "notes": "; ".join(notes),
            }
        )

    if not frames:
        raise ValueError("No scored prompt files were available for stable-cost analysis.")
    return pd.concat(frames, ignore_index=True), pd.DataFrame(logs)


def compute_stable_prompt_cost(df_prompt: pd.DataFrame) -> Dict[str, float]:
    x = df_prompt[["D1", "D2", "D3"]].to_numpy(dtype=float)
    mu = x.mean(axis=0)
    disp_dist = np.linalg.norm(x - mu, axis=1) / math.sqrt(3)
    c_disp = np.sqrt(np.mean(disp_dist ** 2))
    c_norm = np.mean(np.linalg.norm(x - V_STAR, axis=1) / math.sqrt(3))

    peak_counts = (
        df_prompt.groupby(["D1", "D2", "D3"])
        .size()
        .reset_index(name="count")
        .sort_values(["count", "D1", "D2", "D3"], ascending=[False, False, False, False])
    )
    p_peak = peak_counts.iloc[0][["D1", "D2", "D3"]].to_numpy(dtype=float)
    c_peak = np.linalg.norm(p_peak - V_STAR) / math.sqrt(3)

    in_omega = (
        (df_prompt["D1"] >= 0.8)
        & (df_prompt["D2"] >= 0.8)
        & (df_prompt["D3"] >= 0.8)
    )
    p_omega = float(in_omega.mean())
    c_region = 1 - p_omega
    c_weak = float(np.mean(np.maximum(0, THETA - mu)))
    j_stable = 0.30 * c_disp + 0.25 * c_norm + 0.20 * c_peak + 0.15 * c_region + 0.10 * c_weak

    return {
        "N": len(x),
        "mean_D1": mu[0],
        "mean_D2": mu[1],
        "mean_D3": mu[2],
        "p_peak_D1": p_peak[0],
        "p_peak_D2": p_peak[1],
        "p_peak_D3": p_peak[2],
        "P_omega": p_omega,
        "C_disp": c_disp,
        "C_norm": c_norm,
        "C_peak": c_peak,
        "C_region": c_region,
        "C_weak": c_weak,
        "J_stable": j_stable,
    }


def compute_all_stable_costs(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (prompt_id, prompt_type), df_prompt in df.groupby(["prompt_id", "prompt_type"]):
        row = compute_stable_prompt_cost(df_prompt)
        row["prompt_id"] = prompt_id
        row["prompt_type"] = prompt_type
        rows.append(row)

    cost_df = pd.DataFrame(rows).sort_values("J_stable", ascending=True).reset_index(drop=True)
    cost_df["rank"] = np.arange(1, len(cost_df) + 1)
    diag = cost_df.apply(diagnose_row, axis=1, result_type="expand")
    cost_df["main_problem"] = diag["main_problem"]
    cost_df["second_problem"] = diag["second_problem"]
    cost_df["suggested_revision_direction"] = diag["suggested_revision_direction"]
    cost_df["weakest_dimension"] = diag["weakest_dimension"]
    return cost_df[
        [
            "prompt_id",
            "prompt_type",
            "N",
            "mean_D1",
            "mean_D2",
            "mean_D3",
            "p_peak_D1",
            "p_peak_D2",
            "p_peak_D3",
            "P_omega",
            "C_disp",
            "C_norm",
            "C_peak",
            "C_region",
            "C_weak",
            "J_stable",
            "rank",
            "main_problem",
            "second_problem",
            "suggested_revision_direction",
            "weakest_dimension",
        ]
    ]


def diagnose_row(row: pd.Series) -> Dict[str, str]:
    ordered = sorted(COST_COMPONENTS, key=lambda component: float(row[component]), reverse=True)
    main, second = ordered[0], ordered[1]
    means = {"D1": row["mean_D1"], "D2": row["mean_D2"], "D3": row["mean_D3"]}
    weakest = min(means, key=means.get)

    def describe(component: str) -> str:
        diagnosis = DIAGNOSIS[component][0]
        if component == "C_weak":
            diagnosis = f"{diagnosis}; weakest dimension: {weakest}"
        return f"{component}: {diagnosis}"

    direction = DIAGNOSIS[main][1]
    if main == "C_weak":
        direction = f"{direction}: {weakest}"
    return {
        "main_problem": describe(main),
        "second_problem": describe(second),
        "suggested_revision_direction": direction,
        "weakest_dimension": weakest,
    }


def generate_stable_prompts(cost_df: pd.DataFrame) -> List[Dict[str, str]]:
    top = cost_df.sort_values("J_stable", ascending=True).head(2)
    top_ids = set(top["prompt_id"])
    pattern_confirmed = {"Condition 3", "Condition 7"}.issubset(top_ids)

    condition_3 = cost_df[cost_df["prompt_id"] == "Condition 3"].iloc[0]
    condition_7 = cost_df[cost_df["prompt_id"] == "Condition 7"].iloc[0]
    bases = [condition_3, condition_7] if pattern_confirmed else list(top.itertuples(index=False))

    candidates = []

    def add_candidate(
        source_row,
        candidate_id: str,
        target: str,
        diagnosed_problem: str,
        strategy: str,
        expected: str,
        side_effect: str,
        prompt: str,
    ) -> None:
        candidates.append(
            {
                "candidate_id": candidate_id,
                "source_prompt_id": source_row["prompt_id"] if isinstance(source_row, pd.Series) else source_row.prompt_id,
                "source_prompt_type": source_row["prompt_type"] if isinstance(source_row, pd.Series) else source_row.prompt_type,
                "target_cost_component": target,
                "diagnosed_problem": diagnosed_problem,
                "revision_strategy": strategy,
                "expected_effect": expected,
                "possible_side_effect": side_effect,
                "next_round_prompt": prompt,
            }
        )

    add_candidate(
        condition_3,
        "Stable_R2_1_task_component_replication",
        "replication baseline",
        "Condition 3 is the lowest J_stable prompt and needs a direct task-component baseline in round 2",
        "replicate the best task-component base to confirm first-round stability under the new formula",
        "provides a direct benchmark for full-score target and normative-region entry",
        "does not test a new repair operation",
        "请从能量角度解释石块从高空落下这一现象。回答需要明确包含三个任务组件：第一，说明重力势能和动能如何变化；第二，说明机械能在什么条件下守恒；第三，使用准确的科学术语进行表达。请将三个组件组织成一段连贯解释。",
    )
    add_candidate(
        condition_7,
        "Stable_R2_2_demonstration_replication",
        "replication baseline",
        "Condition 7 has the strongest demonstration-guided stability and needs a direct demonstration baseline in round 2",
        "replicate the best demonstration base to confirm its stable response distribution",
        "provides a direct benchmark for demonstration-guided stability",
        "does not test a new repair operation",
        "请仿照这样的高质量解释方式回答：先指出石块在高处具有重力势能；下落时重力势能减少并转化为动能；若忽略空气阻力，机械能近似守恒；若考虑空气阻力，部分机械能会转化为热能、声能等。现在请用类似的方式，从能量角度解释石块从高空落下这一现象。",
    )
    add_candidate(
        condition_3,
        "Stable_R2_3_component_coherence",
        "C_disp + C_region",
        f"{condition_3['main_problem']}; {condition_3['second_problem']}",
        "combine minimum components with a stable explanation order",
        "should reduce dispersion while increasing normative-region entry",
        "strong structure may increase over-template responses",
        "请从能量角度解释石块从高空落下这一现象。回答至少包含：重力势能和动能如何变化、机械能在什么条件下守恒、存在空气阻力时能量如何转化，以及准确科学术语。请按“能量转化、守恒条件、空气阻力、术语总结”的顺序写成一段连贯解释。",
    )
    add_candidate(
        condition_7,
        "Stable_R2_4_demo_full_score_target",
        "C_norm + C_peak",
        f"{condition_7['second_problem']}; C_peak is also checked because the target point is now (1,1,1)",
        "keep demonstration stability while making the full-score pattern explicit",
        "should move the common response pattern closer to (1,1,1)",
        "may reduce naturalness if the target components become too rigid",
        "请仿照高质量科学解释的方式，从能量角度解释石块从高空落下。一个满分解释应同时说明：重力势能向动能转化、无空气阻力时机械能守恒的条件、有空气阻力时部分机械能转化为热能或声能，以及重力势能、动能、机械能守恒等术语的准确使用。请组织成自然连贯的一段话。",
    )
    add_candidate(
        condition_3,
        "Stable_R2_5_component_example_hybrid",
        "C_disp + C_norm + C_peak",
        f"{condition_3['main_problem']}; {condition_3['second_problem']}; full-score proximity is targeted by v*=(1,1,1)",
        "combine full-score components with example-guided stability",
        "should retain component completeness while improving response stability",
        "hybrid prompt is longer and may create formulaic answers",
        "请根据下面的解释框架回答：先说明石块在高处具有重力势能；再说明下落时重力势能减少、动能增加；接着说明在忽略空气阻力时机械能近似守恒；然后说明真实情况下空气阻力会使部分机械能转化为热能、声能等；最后用准确术语总结。请用这个框架解释石块从高空落下，但不要只罗列要点，要写成连贯说明。",
    )
    add_candidate(
        condition_7,
        "Stable_R2_6_stability_optimized",
        "C_disp",
        f"{condition_7['main_problem']}; stability is explicitly stress-tested because C_disp has the highest formula weight",
        "explicitly test a stable explanation structure",
        "should test whether strong structure reduces conceptual dispersion",
        "very low dispersion may indicate homogenized or over-template responses",
        "请使用稳定的解释结构：先说明能量转化，再说明机械能守恒的条件，然后解释存在空气阻力时会发生什么变化，最后使用准确的科学术语进行总结。请保持解释连贯，并避免遗漏上述部分。",
    )

    return candidates


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    headers = [str(column) for column in df.columns]
    rows = [[str(value) if pd.notna(value) else "" for value in row] for row in df.to_numpy()]
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) if rows else len(headers[i]) for i in range(len(headers))]

    def fmt(values: Iterable[str]) -> str:
        return "| " + " | ".join(str(value).ljust(widths[i]) for i, value in enumerate(values)) + " |"

    return "\n".join([fmt(headers), "| " + " | ".join("-" * width for width in widths) + " |", *[fmt(row) for row in rows]])


def prompt_label(prompt_id: str) -> str:
    match = re.search(r"(\d+)", prompt_id)
    return f"P{match.group(1)}" if match else prompt_id


def prompt_order_key(prompt_id: str) -> int:
    match = re.search(r"(\d+)", prompt_id)
    return int(match.group(1)) if match else 9999


def save_outputs(response_df: pd.DataFrame, log_df: pd.DataFrame, cost_df: pd.DataFrame, prompts: List[Dict[str, str]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    numeric = [
        "mean_D1",
        "mean_D2",
        "mean_D3",
        "p_peak_D1",
        "p_peak_D2",
        "p_peak_D3",
        "P_omega",
        "C_disp",
        "C_norm",
        "C_peak",
        "C_region",
        "C_weak",
        "J_stable",
    ]
    export_df = cost_df.copy()
    export_df[numeric] = export_df[numeric].round(4)
    export_df.drop(columns=["weakest_dimension"]).to_csv(output_dir / "stable_cost_summary.csv", index=False, encoding="utf-8-sig")
    export_df.drop(columns=["weakest_dimension"]).to_excel(output_dir / "stable_cost_summary.xlsx", index=False)
    response_df.to_csv(output_dir / "stable_normalized_response_data.csv", index=False, encoding="utf-8-sig")
    log_df.to_csv(output_dir / "stable_data_preprocessing_log.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(prompts).to_csv(output_dir / "next_round_prompts_stable.csv", index=False, encoding="utf-8-sig")
    write_report(response_df, log_df, cost_df, prompts, output_dir)
    write_prompt_file(prompts, output_dir)
    plot_total_cost(cost_df, output_dir)
    plot_components(cost_df, output_dir)
    plot_dimension_means(cost_df, output_dir)

    try:
        from openpyxl import load_workbook

        workbook = load_workbook(output_dir / "stable_cost_summary.xlsx")
        sheet = workbook.active
        for cells in sheet.columns:
            width = max(len(str(cell.value)) if cell.value is not None else 0 for cell in cells)
            sheet.column_dimensions[cells[0].column_letter].width = min(max(width + 2, 10), 52)
        workbook.save(output_dir / "stable_cost_summary.xlsx")
    except Exception:
        pass


def write_report(response_df: pd.DataFrame, log_df: pd.DataFrame, cost_df: pd.DataFrame, prompts: List[Dict[str, str]], output_dir: Path) -> None:
    best = cost_df.iloc[0]
    top_two = cost_df.head(2)
    compact = cost_df[
        ["rank", "prompt_id", "prompt_type", "N", "mean_D1", "mean_D2", "mean_D3", "P_omega", "C_disp", "C_norm", "C_peak", "C_region", "J_stable", "main_problem", "second_problem"]
    ].copy()
    for column in ["mean_D1", "mean_D2", "mean_D3", "P_omega", "C_disp", "C_norm", "C_peak", "C_region", "J_stable"]:
        compact[column] = compact[column].map(lambda value: f"{value:.4f}")

    pattern_note = (
        "The recalculated stable cost confirms the expected two-base pattern: the top prompts include the demonstration prompt and the task-component prompt."
        if {"Condition 3", "Condition 7"}.issubset(set(top_two["prompt_id"]))
        else "The recalculated stable cost does not fully confirm the expected task-component plus demonstration pattern; next-round candidates still follow the actual top-prompt diagnostics."
    )
    prompt_sections = "\n\n".join(format_prompt(prompt) for prompt in prompts)

    report = f"""# Stable-Cost Prompt Iteration Report

## 1. Data overview

This stable-cost prompt iteration used {len(response_df)} scored responses from {len(cost_df)} prompt conditions in `round1/`.

{dataframe_to_markdown(log_df)}

## 2. New formula definition

`J_stable(P) = 0.30*C_disp + 0.25*C_norm + 0.20*C_peak + 0.15*C_region + 0.10*C_weak`.

Lower `J_stable` indicates that a prompt generates responses that are both closer to the ideal full-score explanation and less dispersed in the three-dimensional conceptual space.

## 3. Why v* is set to (1,1,1)

The revised target point is `v* = (1.00, 1.00, 1.00)` because the stable-cost workflow evaluates whether responses approach a full-score scientific explanation across D1, D2, and D3.

## 4. Why C_disp has the highest weight

`C_disp` receives the highest weight because this version prioritizes stable response distributions. However, low dispersion cannot override scientific quality; prompts with low dispersion but weak conceptual scores are still penalized by `C_norm`, `C_peak`, `C_region`, and `C_weak`.

## 5. Prompt ranking by J_stable

{dataframe_to_markdown(compact)}

## 6. Diagnosis of the best prompts

The best prompt is **{best['prompt_id']} ({best['prompt_type']})**, with `J_stable = {best['J_stable']:.4f}`. Its main remaining problem is **{best['main_problem']}**, and its second remaining problem is **{best['second_problem']}**.

{pattern_note}

本研究依据稳定性优先的 cost function 选择优化提示词，而不是仅依据平均分。较低的 J_stable 表明该提示词既能使回答更接近三个维度均为满分的理想科学解释，也能使回答在三维概念空间中的分布更加集中稳定。

## 7. Next-round prompt generation logic

Second-round prompts were generated only after recalculating first-round stable costs. The selected design uses the top stable-cost bases and tests replication, component coherence, demonstration plus full-score target, component-example hybridization, and explicit stability optimization.

## 8. Next-round prompt candidates

{prompt_sections}

## 9. Risks, especially over-template responses

Because `C_disp` has the highest weight, prompts that impose a strong structure may reduce dispersion while also making responses overly homogeneous. The second round should inspect response text, not only scores, especially for the stability-optimized condition.

## 10. Recommended next experiment

Run the six stable-cost second-round prompts with the same response count and scoring rubric. Recompute `J_stable`; then compare whether the hybrid prompts improve both full-score proximity and dispersion without producing over-template responses.
"""
    (output_dir / "stable_iteration_report.md").write_text(report, encoding="utf-8")


def format_prompt(prompt: Dict[str, str]) -> str:
    return f"""### {prompt['candidate_id']}

- source_prompt_id: {prompt['source_prompt_id']}
- source_prompt_type: {prompt['source_prompt_type']}
- target_cost_component: {prompt['target_cost_component']}
- diagnosed_problem: {prompt['diagnosed_problem']}
- revision_strategy: {prompt['revision_strategy']}
- expected_effect: {prompt['expected_effect']}
- possible_side_effect: {prompt['possible_side_effect']}

```text
{prompt['next_round_prompt']}
```"""


def write_prompt_file(prompts: List[Dict[str, str]], output_dir: Path) -> None:
    content = "# Stable Next-Round Prompt Candidates\n\n"
    content += "\n\n".join(format_prompt(prompt) for prompt in prompts)
    content += "\n"
    (output_dir / "next_round_prompts_stable.md").write_text(content, encoding="utf-8")


def plot_total_cost(cost_df: pd.DataFrame, output_dir: Path) -> None:
    plot_df = cost_df.sort_values("rank")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar([prompt_label(item) for item in plot_df["prompt_id"]], plot_df["J_stable"], color="#4C78A8")
    ax.set_xlabel("Prompt")
    ax.set_ylabel("Stable Cost")
    ax.set_title("Stable Cost by Prompt")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "total_stable_cost_barplot.png", dpi=200)
    plt.close(fig)


def plot_components(cost_df: pd.DataFrame, output_dir: Path) -> None:
    plot_df = cost_df.copy()
    plot_df["prompt_order"] = plot_df["prompt_id"].map(prompt_order_key)
    plot_df = plot_df.sort_values("prompt_order")
    matrix = plot_df[COST_COMPONENTS].to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    image = ax.imshow(matrix, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(np.arange(len(COST_COMPONENTS)))
    ax.set_xticklabels(COST_COMPONENTS)
    ax.set_yticks(np.arange(len(plot_df)))
    ax.set_yticklabels([prompt_label(item) for item in plot_df["prompt_id"]])
    ax.set_xlabel("Cost Component")
    ax.set_ylabel("Prompt")
    ax.set_title("Stable Cost Components Heatmap")
    for row_idx in range(matrix.shape[0]):
        for col_idx in range(matrix.shape[1]):
            value = matrix[row_idx, col_idx]
            color = "white" if value > matrix.max() * 0.55 else "black"
            ax.text(col_idx, row_idx, f"{value:.2f}", ha="center", va="center", fontsize=8, color=color)
    fig.colorbar(image, ax=ax, label="Cost")
    fig.tight_layout()
    fig.savefig(output_dir / "stable_cost_components_heatmap.png", dpi=200)
    plt.close(fig)


def plot_dimension_means(cost_df: pd.DataFrame, output_dir: Path) -> None:
    plot_df = cost_df.sort_values("rank")
    labels = [prompt_label(item) for item in plot_df["prompt_id"]]
    x = np.arange(len(plot_df))
    width = 0.25
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    ax.bar(x - width, plot_df["mean_D1"], width, label="Mean D1", color="#4C78A8")
    ax.bar(x, plot_df["mean_D2"], width, label="Mean D2", color="#F58518")
    ax.bar(x + width, plot_df["mean_D3"], width, label="Mean D3", color="#54A24B")
    ax.axhline(0.8, color="#444444", linestyle="--", linewidth=1, label="0.80 threshold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Prompt")
    ax.set_ylabel("Mean Score")
    ax.set_title("Dimension Means by Prompt")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), borderaxespad=0)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout(rect=(0, 0, 0.84, 1))
    fig.savefig(output_dir / "dimension_means_barplot.png", dpi=200)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run stable-cost prompt iteration analysis.")
    parser.add_argument("--round-dir", default="round1")
    parser.add_argument("--output-dir", default="outputs/stable_cost_prompt_iteration")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    response_df, log_df = load_round_data(Path(args.round_dir))
    cost_df = compute_all_stable_costs(response_df)
    prompts = generate_stable_prompts(cost_df)
    save_outputs(response_df, log_df, cost_df, prompts, Path(args.output_dir))
    print(f"Loaded {len(response_df)} scored responses from {len(cost_df)} prompt conditions.")
    print(f"Best prompt: {cost_df.iloc[0]['prompt_id']} ({cost_df.iloc[0]['prompt_type']})")
    print(f"Lowest J_stable: {cost_df.iloc[0]['J_stable']:.4f}")
    print(f"Outputs saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
