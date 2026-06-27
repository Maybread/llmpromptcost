from __future__ import annotations

import argparse
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

matplotlib_cache_dir = Path("outputs") / ".matplotlib"
matplotlib_cache_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_cache_dir.resolve()))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


TARGET_POINT = np.array([0.80, 1.00, 1.00], dtype=float)
THETA = np.array([0.80, 0.80, 0.80], dtype=float)
COST_COMPONENTS = ["C_norm", "C_peak", "C_region", "C_weak", "C_disp"]

PROMPT_TYPES = {
    1: "Baseline open prompt",
    2: "Role prompt",
    3: "Task-component prompt",
    4: "Reasoning scaffold prompt",
    5: "Knowledge-grounded prompt (RAG)",
    6: "Self-checking prompt",
    7: "Demonstration prompt",
}

REVISION_DIRECTIONS = {
    "C_norm": (
        "Overall normative distance is high",
        "Strengthen scientific completeness and normative explanation",
    ),
    "C_peak": (
        "Density peak is not in the desired region",
        "Clarify the components of a high-quality explanation",
    ),
    "C_region": (
        "Too few responses enter the normative region",
        "Set minimum required explanation components",
    ),
    "C_weak": (
        "One dimension is underdeveloped",
        "Repair the weakest D1/D2/D3 dimension",
    ),
    "C_disp": (
        "Responses are too dispersed",
        "Add explanation order and coherence constraints",
    ),
}


@dataclass
class LoadLog:
    source_file: str
    prompt_id: str
    prompt_type: str
    encoding: str
    original_rows: int
    retained_rows: int
    removed_missing_score_rows: int
    normalization_method: str
    missing_required_columns: str
    notes: str


def load_experiment_data(path: Path) -> Tuple[pd.DataFrame, str]:
    encodings = ["utf-8-sig", "utf-8", "gb18030", "gbk"]
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            df = pd.read_csv(path, encoding=encoding)
            return df, encoding
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(f"Could not read {path} with supported encodings") from last_error


def prompt_number_from_path(path: Path) -> int:
    match = re.search(r"prompt1-(\d+)", path.stem, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"Cannot infer prompt number from file name: {path.name}")
    return int(match.group(1))


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "prompt_id": {"prompt_id", "condition", "prompt", "prompt_name"},
        "prompt_type": {"prompt_type", "prompt 类型", "prompt type"},
        "response_id": {"response_id", "id", "index", "序号"},
        "response_text": {"response_text", "answer", "response", "output", "回答"},
        "D1": {"d1", "dim1", "score1", "score_1", "core_concept"},
        "D2": {"d2", "dim2", "score2", "score_2", "condition_model"},
        "D3": {"d3", "dim3", "score3", "score_3", "terminology"},
    }

    rename_map = {}
    normalized_columns = {
        column: re.sub(r"\s+", " ", str(column).strip()).lower()
        for column in df.columns
    }
    for canonical, options in aliases.items():
        for column, normalized in normalized_columns.items():
            if normalized in options:
                rename_map[column] = canonical
                break

    return df.rename(columns=rename_map)


def normalize_scores(df: pd.DataFrame) -> Tuple[pd.DataFrame, str, int]:
    df = df.copy()
    score_columns = ["D1", "D2", "D3"]
    for column in score_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    original_rows = len(df)
    df = df.dropna(subset=score_columns).copy()
    removed_rows = original_rows - len(df)

    score_min = df[score_columns].min().min()
    score_max = df[score_columns].max().max()
    if score_min >= 0 and score_max <= 1:
        method = "scores already in [0, 1]"
    elif score_min >= 0 and score_max <= 2:
        df[score_columns] = df[score_columns] / 2.0
        method = "converted from [0, 2] to [0, 1]"
    else:
        raise ValueError(
            f"Score range is outside supported intervals: min={score_min}, max={score_max}"
        )

    return df, method, removed_rows


def compute_prompt_cost(df_prompt: pd.DataFrame) -> Dict[str, float]:
    x = df_prompt[["D1", "D2", "D3"]].to_numpy(dtype=float)
    n = len(x)
    mu = x.mean(axis=0)

    c_norm = np.mean(np.linalg.norm(x - TARGET_POINT, axis=1) / math.sqrt(3))

    peak_counts = (
        df_prompt.groupby(["D1", "D2", "D3"])
        .size()
        .reset_index(name="count")
        .sort_values(["count", "D1", "D2", "D3"], ascending=[False, False, False, False])
    )
    p_peak = peak_counts.iloc[0][["D1", "D2", "D3"]].to_numpy(dtype=float)
    c_peak = np.linalg.norm(p_peak - TARGET_POINT) / math.sqrt(3)

    in_omega = (
        (df_prompt["D1"] >= 0.80)
        & (df_prompt["D2"] >= 0.80)
        & (df_prompt["D3"] >= 0.80)
    )
    p_omega = float(in_omega.mean())
    c_region = 1 - p_omega

    c_weak = float(np.mean(np.maximum(0, THETA - mu)))
    c_disp = np.mean(np.linalg.norm(x - mu, axis=1) / math.sqrt(3))

    j_total = (
        0.30 * c_norm
        + 0.25 * c_peak
        + 0.20 * c_region
        + 0.15 * c_weak
        + 0.10 * c_disp
    )

    return {
        "N": n,
        "mean_D1": mu[0],
        "mean_D2": mu[1],
        "mean_D3": mu[2],
        "p_peak_D1": p_peak[0],
        "p_peak_D2": p_peak[1],
        "p_peak_D3": p_peak[2],
        "P_omega": p_omega,
        "C_norm": c_norm,
        "C_peak": c_peak,
        "C_region": c_region,
        "C_weak": c_weak,
        "C_disp": c_disp,
        "J_total": j_total,
    }


def compute_all_prompt_costs(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (prompt_id, prompt_type), df_prompt in df.groupby(["prompt_id", "prompt_type"]):
        cost = compute_prompt_cost(df_prompt)
        cost["prompt_id"] = prompt_id
        cost["prompt_type"] = prompt_type
        rows.append(cost)

    cost_df = pd.DataFrame(rows)
    cost_df = cost_df.sort_values("J_total", ascending=True).reset_index(drop=True)
    cost_df["rank"] = np.arange(1, len(cost_df) + 1)
    diagnostics = cost_df.apply(diagnose_prompt, axis=1, result_type="expand")
    cost_df["main_problem"] = diagnostics["main_problem"]
    cost_df["suggested_revision_direction"] = diagnostics["suggested_revision_direction"]
    cost_df["weakest_dimension"] = diagnostics["weakest_dimension"]

    ordered_columns = [
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
        "C_norm",
        "C_peak",
        "C_region",
        "C_weak",
        "C_disp",
        "J_total",
        "rank",
        "main_problem",
        "suggested_revision_direction",
        "weakest_dimension",
    ]
    return cost_df[ordered_columns]


def diagnose_prompt(row: pd.Series) -> Dict[str, str]:
    highest_component = max(COST_COMPONENTS, key=lambda component: float(row[component]))
    diagnosis, direction = REVISION_DIRECTIONS[highest_component]
    means = {"D1": row["mean_D1"], "D2": row["mean_D2"], "D3": row["mean_D3"]}
    weakest_dimension = min(means, key=means.get)
    if highest_component == "C_weak":
        diagnosis = f"{diagnosis}; weakest dimension: {weakest_dimension}"
        direction = f"{direction}: {weakest_dimension}"
    return {
        "main_problem": f"{highest_component}: {diagnosis}",
        "suggested_revision_direction": direction,
        "weakest_dimension": weakest_dimension,
    }


def select_prompts_for_revision(cost_df: pd.DataFrame, top_k: int = 2) -> pd.DataFrame:
    return cost_df.sort_values("J_total", ascending=True).head(top_k).copy()


def strategy_for_component(component: str, weakest_dimension: str) -> Dict[str, str]:
    strategies = {
        "C_norm": {
            "operation": "add complete scientific explanation requirements",
            "prompt": (
                "请从能量角度解释石块从高空落下这一现象。你的解释应清楚说明相关能量如何发生变化，"
                "说明这种变化背后的科学原理；在必要时指出解释成立的条件，并使用恰当的科学术语。"
            ),
            "expected": "responses should move closer to the normative conceptual target",
            "side_effect": "the prompt may become slightly longer and more directive",
        },
        "C_peak": {
            "operation": "make the components of a complete explanation explicit",
            "prompt": (
                "请从能量角度解释石块从高空落下这一现象。一个完整的解释应包括：能量变化过程、"
                "该过程成立的条件，以及关键科学术语的准确使用。请将这些内容组织成一段连贯解释。"
            ),
            "expected": "the most frequent answer pattern should move toward the normative region",
            "side_effect": "answers may become more uniform",
        },
        "C_region": {
            "operation": "set minimum answer requirements",
            "prompt": (
                "请从能量角度解释石块从高空落下这一现象。回答中至少应包含三个方面：相关能量如何变化、"
                "解释这一变化时需要考虑的条件，以及恰当使用科学术语。请避免只给出笼统描述。"
            ),
            "expected": "a larger proportion of responses should enter the normative region",
            "side_effect": "minimum requirements may reduce stylistic diversity",
        },
        "C_disp": {
            "operation": "add explanation order and coherence constraints",
            "prompt": (
                "请从能量角度解释石块从高空落下这一现象。请按照“初始状态、能量变化过程、需要考虑的条件、"
                "科学术语总结”的顺序进行连贯解释，避免遗漏关键环节。"
            ),
            "expected": "responses should become more stable and coherent",
            "side_effect": "too much structure may create over-template responses",
        },
    }

    if component == "C_weak":
        weak_prompts = {
            "D1": (
                "请从能量角度解释石块从高空落下这一现象。请重点说明初始状态、下落过程中能量形式的变化，"
                "以及这些能量变化之间的关系。必要时说明相关条件，并使用恰当科学术语。"
            ),
            "D2": (
                "请从能量角度解释石块从高空落下这一现象。除说明能量变化外，还要明确指出该解释在什么条件下成立；"
                "如果理想情况和真实情况中的能量变化不同，请分别说明。请使用恰当科学术语。"
            ),
            "D3": (
                "请从能量角度解释石块从高空落下这一现象。请在说明能量变化和相关条件的同时，"
                "使用准确的科学术语表达，不要只使用日常化或模糊表述。"
            ),
        }
        return {
            "operation": f"repair the weakest dimension {weakest_dimension}",
            "prompt": weak_prompts[weakest_dimension],
            "expected": f"the mean score of {weakest_dimension} should increase",
            "side_effect": "emphasis on one dimension may crowd out other explanation elements",
        }

    return strategies[component]


def problem_for_component(component: str, weakest_dimension: str) -> str:
    diagnosis = REVISION_DIRECTIONS[component][0]
    if component == "C_weak":
        return f"{component}: {diagnosis}; weakest dimension: {weakest_dimension}"
    return f"{component}: {diagnosis}"


def repair_clause(component: str, weakest_dimension: str) -> str:
    clauses = {
        "C_norm": "完整说明能量变化、科学原理、适用条件和关键术语。",
        "C_peak": "明确包含能量变化过程、成立条件和关键科学术语，使常见回答模式更完整。",
        "C_region": "至少包含能量如何变化、需要考虑的条件、恰当科学术语三个方面。",
        "C_disp": "按照初始状态、能量变化过程、条件、术语总结的顺序连贯解释。",
    }
    if component == "C_weak":
        weak_clauses = {
            "D1": "重点补足初始状态、能量形式变化及能量变化关系。",
            "D2": "明确说明解释成立的条件，并区分理想情况和真实情况。",
            "D3": "使用准确科学术语，避免日常化或模糊表述。",
        }
        return weak_clauses[weakest_dimension]
    return clauses[component]


def generate_next_round_prompts(best_rows: pd.DataFrame) -> List[Dict[str, str]]:
    generated = []
    for _, row in best_rows.iterrows():
        components = sorted(COST_COMPONENTS, key=lambda component: float(row[component]), reverse=True)
        highest, second = components[0], components[1]
        weakest_dimension = str(row["weakest_dimension"])
        source_prompt_id = str(row["prompt_id"])
        source_prompt_text = (
            "Original prompt text was not provided in the input files; "
            f"available source condition is {row['prompt_type']}."
        )

        strategy_high = strategy_for_component(highest, weakest_dimension)
        strategy_second = strategy_for_component(second, weakest_dimension)
        combined_prompt = (
            "请从能量角度解释石块从高空落下这一现象。请用一段连贯文字完成解释，并同时满足以下要求："
            f"第一，{repair_clause(highest, weakest_dimension)}"
            f"第二，{repair_clause(second, weakest_dimension)}"
            "请避免只给出笼统结论。"
        )

        variants = [
            (
                "target_highest_component",
                highest,
                problem_for_component(highest, weakest_dimension),
                strategy_high["operation"],
                strategy_high["expected"],
                strategy_high["side_effect"],
                strategy_high["prompt"],
            ),
            (
                "target_second_component",
                second,
                problem_for_component(second, weakest_dimension),
                strategy_second["operation"],
                strategy_second["expected"],
                strategy_second["side_effect"],
                strategy_second["prompt"],
            ),
            (
                "combined_repair",
                f"{highest} + {second}",
                f"{problem_for_component(highest, weakest_dimension)}; {problem_for_component(second, weakest_dimension)}",
                f"combine {strategy_high['operation']} and {strategy_second['operation']}",
                "the answer distribution should improve on the two largest remaining cost sources",
                "combined constraints may increase prompt length",
                combined_prompt,
            ),
            (
                "compressed_variant",
                highest,
                problem_for_component(highest, weakest_dimension),
                "compress the highest-component repair into a shorter instruction",
                "retain the main repair while reducing prompt length",
                "shorter wording may provide weaker guidance",
                (
                    "请从能量角度解释石块从高空落下，简洁说明能量变化、成立条件和关键科学术语，"
                    "避免笼统描述。"
                ),
            ),
            (
                "natural_expression_variant",
                f"{highest} + over-template risk",
                f"{problem_for_component(highest, weakest_dimension)}; possible over-template risk",
                "make the repair sound more natural and less template-like",
                "reduce response homogenization while keeping cost-guided requirements",
                "less rigid structure may slightly increase dispersion",
                (
                    "请像给学生讲解一样，从能量角度说明石块为什么会从高空落下。"
                    "讲清楚能量从哪里来、如何变化、哪些条件会影响解释，并自然地使用准确科学术语。"
                ),
            ),
        ]

        for index, (variant_type, target, diagnosed_problem, operation, expected, side_effect, prompt) in enumerate(
            variants, start=1
        ):
            generated.append(
                {
                    "candidate_id": f"{source_prompt_id}_v{index}",
                    "source_prompt_id": source_prompt_id,
                    "source_prompt_text": source_prompt_text,
                    "source_prompt_type": str(row["prompt_type"]),
                    "variant_type": variant_type,
                    "target_cost_component": target,
                    "diagnosed_problem": diagnosed_problem,
                    "revision_operation": operation,
                    "expected_effect": expected,
                    "possible_side_effect": side_effect,
                    "next_round_prompt": prompt,
                }
            )
    return generated


def load_round_data(round_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    frames = []
    logs: List[LoadLog] = []

    for csv_path in sorted(round_dir.glob("*.csv")):
        prompt_number = prompt_number_from_path(csv_path)
        prompt_id = f"Condition {prompt_number}"
        prompt_type = PROMPT_TYPES.get(prompt_number, f"Prompt {prompt_number}")
        raw_df, encoding = load_experiment_data(csv_path)
        original_rows = len(raw_df)
        df = standardize_columns(raw_df)

        missing_columns = [column for column in ["response_id", "D1", "D2", "D3"] if column not in df.columns]
        notes = []
        if "response_text" not in df.columns:
            df["response_text"] = ""
            notes.append("response_text missing; filled with empty string for cost computation")
        if missing_columns:
            logs.append(
                LoadLog(
                    source_file=csv_path.name,
                    prompt_id=prompt_id,
                    prompt_type=prompt_type,
                    encoding=encoding,
                    original_rows=original_rows,
                    retained_rows=0,
                    removed_missing_score_rows=0,
                    normalization_method="not applied",
                    missing_required_columns=", ".join(missing_columns),
                    notes="file skipped",
                )
            )
            continue

        df, method, removed_rows = normalize_scores(df)
        df["prompt_id"] = prompt_id
        df["prompt_type"] = prompt_type
        df["source_file"] = csv_path.name
        frames.append(df[["prompt_id", "prompt_type", "response_id", "response_text", "D1", "D2", "D3", "source_file"]])
        logs.append(
            LoadLog(
                source_file=csv_path.name,
                prompt_id=prompt_id,
                prompt_type=prompt_type,
                encoding=encoding,
                original_rows=original_rows,
                retained_rows=len(df),
                removed_missing_score_rows=removed_rows,
                normalization_method=method,
                missing_required_columns="",
                notes="; ".join(notes),
            )
        )

    if not frames:
        raise ValueError("No usable scored prompt files were found.")

    return pd.concat(frames, ignore_index=True), pd.DataFrame([log.__dict__ for log in logs])


def save_outputs(
    response_df: pd.DataFrame,
    cost_df: pd.DataFrame,
    load_log_df: pd.DataFrame,
    prompts: List[Dict[str, str]],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    numeric_columns = [
        "mean_D1",
        "mean_D2",
        "mean_D3",
        "p_peak_D1",
        "p_peak_D2",
        "p_peak_D3",
        "P_omega",
        "C_norm",
        "C_peak",
        "C_region",
        "C_weak",
        "C_disp",
        "J_total",
    ]
    export_cost_df = cost_df.copy()
    export_cost_df[numeric_columns] = export_cost_df[numeric_columns].round(4)
    export_cost_df.to_csv(output_dir / "cost_summary.csv", index=False, encoding="utf-8-sig")
    export_cost_df.to_excel(output_dir / "cost_summary.xlsx", index=False)

    response_df.to_csv(output_dir / "normalized_response_data.csv", index=False, encoding="utf-8-sig")
    load_log_df.to_csv(output_dir / "data_preprocessing_log.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(prompts).to_csv(output_dir / "next_round_prompts.csv", index=False, encoding="utf-8-sig")

    write_iteration_report(response_df, cost_df, load_log_df, prompts, output_dir)
    write_next_round_prompts(prompts, output_dir)
    plot_total_cost(cost_df, output_dir)
    plot_cost_components(cost_df, output_dir)
    plot_dimension_means(cost_df, output_dir)

    try:
        from openpyxl import load_workbook

        workbook = load_workbook(output_dir / "cost_summary.xlsx")
        worksheet = workbook.active
        for column_cells in worksheet.columns:
            max_length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
            worksheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 10), 48)
        workbook.save(output_dir / "cost_summary.xlsx")
    except Exception:
        pass


def write_iteration_report(
    response_df: pd.DataFrame,
    cost_df: pd.DataFrame,
    load_log_df: pd.DataFrame,
    prompts: List[Dict[str, str]],
    output_dir: Path,
) -> None:
    best = cost_df.sort_values("J_total", ascending=True).iloc[0]
    cost_table = cost_df[
        ["rank", "prompt_id", "prompt_type", "N", "mean_D1", "mean_D2", "mean_D3", "P_omega", "J_total", "main_problem"]
    ].copy()
    for column in ["mean_D1", "mean_D2", "mean_D3", "P_omega", "J_total"]:
        cost_table[column] = cost_table[column].map(lambda value: f"{value:.4f}")

    normalization_summary = dataframe_to_markdown(load_log_df[
        ["source_file", "prompt_id", "encoding", "original_rows", "retained_rows", "normalization_method", "notes"]
    ])
    cost_markdown = dataframe_to_markdown(cost_table)
    prompt_count = len(cost_df)
    response_count = len(response_df)
    close_costs = cost_df["J_total"].sort_values().head(2)
    if len(close_costs) >= 2 and abs(close_costs.iloc[1] - close_costs.iloc[0]) < 0.01:
        similarity_note = (
            "The top two prompts have very similar total costs; bootstrap confidence intervals or a larger sample "
            "would make the ranking more stable."
        )
    else:
        similarity_note = "The current ranking has a visible separation between the best prompt and the next prompt."

    prompt_sections = "\n\n".join(format_prompt_candidate(prompt) for prompt in prompts)

    report = f"""# Cost-Function-Guided Prompt Iteration Report

## 1. Data overview

The analysis used {response_count} response-level scored records across {prompt_count} prompt conditions.
Files were loaded from `round1/`. Condition 1 is a score-only file; its `response_text` was not available, so it was retained for cost computation with an empty response-text field.

## 2. Score normalization method

Scores were standardized into the [0, 1] interval before cost computation. Rows with missing D1/D2/D3 values were removed if present.

{normalization_summary}

## 3. Cost function definition

The target conceptual point is `v* = (0.80, 1.00, 1.00)`. The normative region is `Omega = {{x | D1 >= 0.80, D2 >= 0.80, D3 >= 0.80}}`.

`J(P) = 0.30*C_norm + 0.25*C_peak + 0.20*C_region + 0.15*C_weak + 0.10*C_disp`.

Lower total cost indicates a better balance among normative proximity, density peak location, normative-region proportion, dimensional weakness, and conceptual dispersion.

## 4. Cost summary and prompt ranking

{cost_markdown}

{similarity_note}

## 5. Current best prompt

The current best prompt is **{best['prompt_id']} ({best['prompt_type']})** with the lowest total cost, `J_total = {best['J_total']:.4f}`.

## 6. Diagnostic interpretation of cost components

For each prompt, the largest remaining cost component was used as the main diagnostic signal. `C_region` indicates insufficient entry into the normative region, `C_peak` indicates that the most frequent response type remains below target, `C_norm` captures overall distance from the target point, `C_weak` marks a weak dimension, and `C_disp` captures response dispersion.

## 7. Why the best prompt is selected by total cost rather than average score

The best prompt is not selected because it has the highest average score. It is selected because it has the lowest total cost, indicating the best overall balance among normative proximity, density peak location, normative-region proportion, dimensional weakness, and conceptual dispersion.

## 8. Remaining problems of the best prompt

The main remaining problem for {best['prompt_id']} is: **{best['main_problem']}**. Its recommended revision direction is: **{best['suggested_revision_direction']}**.

## 9. Next-round prompt generation logic

The next-round prompt candidates were generated from the top 1-2 prompts ranked by total cost. For each selected prompt, variants target the largest cost component, the second-largest cost component, a combined repair, a compressed version, and a natural-expression version to reduce over-template risk.

## 10. Next-round prompt candidates

{prompt_sections}

## 11. Potential risks, including over-template responses

Very low dispersion can indicate response homogenization. Some next-round candidates deliberately add structure, which may reduce dispersion but can also make answers too template-like. The natural-expression variants are included to test whether conceptual quality can improve without excessive standardization.

## 12. Recommended next experiment

Run the next-round candidates with the same sample size and scoring rubric, then recompute the same cost components. If the top candidates remain close in `J_total`, add bootstrap confidence intervals or increase the response sample size before making a final prompt selection.
"""
    (output_dir / "iteration_report.md").write_text(report, encoding="utf-8")


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    headers = [str(column) for column in df.columns]
    rows = [[str(value) if pd.notna(value) else "" for value in row] for row in df.to_numpy()]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows)) if rows else len(headers[index])
        for index in range(len(headers))
    ]

    def format_row(values: Iterable[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[index]) for index, value in enumerate(values)) + " |"

    lines = [
        format_row(headers),
        "| " + " | ".join("-" * width for width in widths) + " |",
    ]
    lines.extend(format_row(row) for row in rows)
    return "\n".join(lines)


def format_prompt_candidate(prompt: Dict[str, str]) -> str:
    return f"""### {prompt['candidate_id']}

- source_prompt_id: {prompt['source_prompt_id']}
- source_prompt_text: {prompt['source_prompt_text']}
- target_cost_component: {prompt['target_cost_component']}
- diagnosed_problem: {prompt['diagnosed_problem']}
- revision_operation: {prompt['revision_operation']}
- expected_effect: {prompt['expected_effect']}
- possible_side_effect: {prompt['possible_side_effect']}

```text
{prompt['next_round_prompt']}
```"""


def write_next_round_prompts(prompts: List[Dict[str, str]], output_dir: Path) -> None:
    content = "# Next-Round Prompt Candidates\n\n"
    content += "\n\n".join(format_prompt_candidate(prompt) for prompt in prompts)
    content += "\n"
    (output_dir / "next_round_prompts.md").write_text(content, encoding="utf-8")


def plot_total_cost(cost_df: pd.DataFrame, output_dir: Path) -> None:
    plot_df = cost_df.sort_values("rank")
    labels = [prompt_label(prompt_id) for prompt_id in plot_df["prompt_id"]]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar(labels, plot_df["J_total"], color="#4C78A8")
    ax.set_xlabel("Prompt")
    ax.set_ylabel("Total Cost")
    ax.set_title("Total Cost by Prompt")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "total_cost_barplot.png", dpi=200)
    plt.close(fig)


def plot_cost_components(cost_df: pd.DataFrame, output_dir: Path) -> None:
    plot_df = cost_df.sort_values("rank")
    matrix = plot_df[COST_COMPONENTS].to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    image = ax.imshow(matrix, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(np.arange(len(COST_COMPONENTS)))
    ax.set_xticklabels(COST_COMPONENTS)
    ax.set_yticks(np.arange(len(plot_df)))
    ax.set_yticklabels([prompt_label(prompt_id) for prompt_id in plot_df["prompt_id"]])
    ax.set_xlabel("Cost Component")
    ax.set_ylabel("Prompt")
    ax.set_title("Cost Components Heatmap")
    for row_index in range(matrix.shape[0]):
        for col_index in range(matrix.shape[1]):
            value = matrix[row_index, col_index]
            text_color = "white" if value > matrix.max() * 0.55 else "black"
            ax.text(col_index, row_index, f"{value:.2f}", ha="center", va="center", fontsize=8, color=text_color)
    fig.colorbar(image, ax=ax, label="Cost")
    fig.tight_layout()
    fig.savefig(output_dir / "cost_components_heatmap.png", dpi=200)
    plt.close(fig)


def plot_dimension_means(cost_df: pd.DataFrame, output_dir: Path) -> None:
    plot_df = cost_df.sort_values("rank")
    labels = [prompt_label(prompt_id) for prompt_id in plot_df["prompt_id"]]
    x = np.arange(len(plot_df))
    width = 0.25
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    ax.bar(x - width, plot_df["mean_D1"], width, label="Mean D1", color="#4C78A8")
    ax.bar(x, plot_df["mean_D2"], width, label="Mean D2", color="#F58518")
    ax.bar(x + width, plot_df["mean_D3"], width, label="Mean D3", color="#54A24B")
    ax.axhline(0.80, color="#444444", linestyle="--", linewidth=1, label="0.80 threshold")
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


def prompt_label(prompt_id: str) -> str:
    match = re.search(r"(\d+)", prompt_id)
    return f"P{match.group(1)}" if match else prompt_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run cost-function-guided prompt iteration analysis.")
    parser.add_argument("--round-dir", default="round1", help="Directory containing current-round CSV files.")
    parser.add_argument(
        "--output-dir",
        default="outputs/cost_function_iteration",
        help="Directory where analysis outputs will be saved.",
    )
    parser.add_argument("--top-k", type=int, default=2, help="Number of top prompts used for next-round revision.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    round_dir = Path(args.round_dir)
    output_dir = Path(args.output_dir)
    response_df, load_log_df = load_round_data(round_dir)
    cost_df = compute_all_prompt_costs(response_df)
    best_rows = select_prompts_for_revision(cost_df, top_k=args.top_k)
    prompts = generate_next_round_prompts(best_rows)
    save_outputs(response_df, cost_df, load_log_df, prompts, output_dir)

    print(f"Loaded {len(response_df)} scored responses from {len(cost_df)} prompt conditions.")
    print(f"Best prompt: {cost_df.iloc[0]['prompt_id']} ({cost_df.iloc[0]['prompt_type']})")
    print(f"Lowest J_total: {cost_df.iloc[0]['J_total']:.4f}")
    print(f"Outputs saved to: {output_dir}")


if __name__ == "__main__":
    main()
