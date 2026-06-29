from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import run_stable_cost_prompt_iteration as stable


ROUND2_DIR = Path("round2")
OUTPUT_DIR = Path("outputs") / "stable_cost_prompt_iteration_round2"

# Round 2 uses a round-specific condition naming scheme.
ROUND2_FILES: List[Tuple[str, str, str]] = [
    ("qwen-prompt1-3.csv", "R1-C3", "Task-component baseline from round 1"),
    ("qwen-prompt1-7.csv", "R1-C7", "Demonstration baseline from round 1"),
    ("PHYSICS-R2-C3-score.csv", "R2-P3*P7", "Round 2 optimized prompt"),
]

WEIGHTS: Dict[str, float] = {
    "C_disp": 0.20,
    "C_norm": 0.20,
    "C_peak": 0.20,
    "C_region": 0.20,
    "C_weak": 0.20,
}


def short_label(prompt_id: str) -> str:
    return prompt_id


def comparison_order(cost_df: pd.DataFrame) -> pd.DataFrame:
    order = {"R1-C3": 1, "R1-C7": 2, "R2-P3*P7": 3}
    return (
        cost_df.assign(_order=cost_df["prompt_id"].map(order).fillna(99))
        .sort_values("_order")
        .drop(columns="_order")
    )


def standardize_round2_columns(csv_path: Path, raw_df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    notes = []

    if csv_path.name == "PHYSICS-R2-C3-score.csv":
        # The new score-only file stores the three scoring dimensions under mixed names.
        df = raw_df.rename(
            columns={
                "ID": "response_id",
                "Score": "D1",
                "score2": "D2",
                "Score_3": "D3",
            }
        )
        if "response_text" not in df.columns:
            df["response_text"] = ""
            notes.append("response_text missing; retained as score-only round2 file")
        notes.append("mapped Score->D1, score2->D2, Score_3->D3")
        return df, "; ".join(notes)

    df = stable.standardize_columns(raw_df)
    if "response_text" not in df.columns:
        df["response_text"] = ""
        notes.append("response_text missing; retained as score-only file")
    return df, "; ".join(notes)


def load_round2_data(round_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    frames = []
    logs = []

    for file_name, prompt_id, prompt_type in ROUND2_FILES:
        csv_path = round_dir / file_name
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing expected round2 file: {csv_path}")

        raw_df, encoding = stable.read_csv_with_encoding(csv_path)
        df, notes = standardize_round2_columns(csv_path, raw_df)
        required = ["response_id", "D1", "D2", "D3"]
        missing = [column for column in required if column not in df.columns]

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
                    "notes": "file skipped; " + notes,
                }
            )
            continue

        df, method, removed = stable.normalize_scores(df)
        df["prompt_id"] = prompt_id
        df["prompt_type"] = prompt_type
        df["source_file"] = csv_path.name
        frames.append(
            df[
                [
                    "prompt_id",
                    "prompt_type",
                    "response_id",
                    "response_text",
                    "D1",
                    "D2",
                    "D3",
                    "source_file",
                ]
            ]
        )
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
                "notes": notes,
            }
        )

    if not frames:
        raise ValueError("No round2 files were available for stable-cost analysis.")
    return pd.concat(frames, ignore_index=True), pd.DataFrame(logs)


def build_component_contributions(cost_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in cost_df.iterrows():
        output = {
            "prompt_id": row["prompt_id"],
            "prompt_type": row["prompt_type"],
            "rank": row["rank"],
            "J_stable": row["J_stable"],
        }
        for component, weight in WEIGHTS.items():
            output[component] = row[component]
            output[f"weighted_{component}"] = row[component] * weight
        rows.append(output)
    return pd.DataFrame(rows)


def save_round2_tables(
    response_df: pd.DataFrame,
    log_df: pd.DataFrame,
    cost_df: pd.DataFrame,
    component_df: pd.DataFrame,
    output_dir: Path,
) -> None:
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
    export_cost = cost_df.copy()
    export_cost[numeric] = export_cost[numeric].round(4)
    export_cost.drop(columns=["weakest_dimension"]).to_csv(
        output_dir / "round2_stable_cost_summary.csv", index=False, encoding="utf-8-sig"
    )
    response_df.to_csv(
        output_dir / "round2_stable_normalized_response_data.csv",
        index=False,
        encoding="utf-8-sig",
    )
    log_df.to_csv(
        output_dir / "round2_stable_data_preprocessing_log.csv",
        index=False,
        encoding="utf-8-sig",
    )

    export_component = component_df.copy()
    component_numeric = [
        column
        for column in export_component.columns
        if column.startswith("C_") or column.startswith("weighted_") or column == "J_stable"
    ]
    export_component[component_numeric] = export_component[component_numeric].round(4)
    export_component.to_csv(
        output_dir / "round2_stable_component_contributions.csv",
        index=False,
        encoding="utf-8-sig",
    )

    try:
        export_cost.drop(columns=["weakest_dimension"]).to_excel(
            output_dir / "round2_stable_cost_summary.xlsx", index=False
        )
        export_component.to_excel(
            output_dir / "round2_stable_component_contributions.xlsx", index=False
        )
    except Exception:
        pass


def plot_total_cost(cost_df: pd.DataFrame, output_dir: Path) -> None:
    plot_df = cost_df.sort_values("rank")
    colors = ["#4C78A8" if item == "R2-P3*P7" else "#9AA0A6" for item in plot_df["prompt_id"]]

    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    ax.bar([short_label(item) for item in plot_df["prompt_id"]], plot_df["J_stable"], color=colors)
    ax.set_xlabel("Prompt condition")
    ax.set_ylabel(r"Stable cost $\mathit{J}_{\mathit{stable}}$")
    ax.set_title("Round 2 Stable Cost by Prompt")
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.8, alpha=0.8)
    fig.tight_layout()
    fig.savefig(output_dir / "round2_total_stable_cost_barplot.png", dpi=300)
    plt.close(fig)


def plot_component_heatmap(cost_df: pd.DataFrame, output_dir: Path) -> None:
    plot_df = comparison_order(cost_df)
    matrix = plot_df[stable.COST_COMPONENTS].to_numpy(dtype=float)

    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    image = ax.imshow(matrix, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(np.arange(len(stable.COST_COMPONENTS)))
    ax.set_xticklabels([stable.COST_COMPONENT_LABELS[item] for item in stable.COST_COMPONENTS])
    ax.set_yticks(np.arange(len(plot_df)))
    ax.set_yticklabels([short_label(item) for item in plot_df["prompt_id"]])
    ax.set_xlabel("Cost component")
    ax.set_ylabel("Prompt condition")
    ax.set_title("Round 2 Stable Cost Components")

    vmax = matrix.max() if matrix.size else 0
    for row_idx in range(matrix.shape[0]):
        for col_idx in range(matrix.shape[1]):
            value = matrix[row_idx, col_idx]
            text_color = "white" if vmax and value > vmax * 0.55 else "black"
            ax.text(col_idx, row_idx, f"{value:.2f}", ha="center", va="center", fontsize=8, color=text_color)

    fig.colorbar(image, ax=ax, label="Cost")
    fig.tight_layout()
    fig.savefig(output_dir / "round2_stable_cost_components_heatmap.png", dpi=300)
    plt.close(fig)


def plot_dimension_means(cost_df: pd.DataFrame, output_dir: Path) -> None:
    plot_df = comparison_order(cost_df)
    labels = [short_label(item) for item in plot_df["prompt_id"]]
    x = np.arange(len(plot_df))
    width = 0.23

    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.bar(x - width, plot_df["mean_D1"], width, label="Mean D1", color="#4C78A8")
    ax.bar(x, plot_df["mean_D2"], width, label="Mean D2", color="#F58518")
    ax.bar(x + width, plot_df["mean_D3"], width, label="Mean D3", color="#54A24B")
    ax.axhline(0.8, color="#555555", linestyle="--", linewidth=1, label="0.80 threshold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Prompt condition")
    ax.set_ylabel("Mean score")
    ax.set_title("Round 2 Dimension Means")
    ax.legend(loc="lower right", frameon=True)
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.8, alpha=0.8)
    fig.tight_layout()
    fig.savefig(output_dir / "round2_dimension_means_barplot.png", dpi=300)
    plt.close(fig)


def plot_weighted_contributions(component_df: pd.DataFrame, output_dir: Path) -> None:
    plot_df = component_df.sort_values("rank")
    labels = [short_label(item) for item in plot_df["prompt_id"]]
    x = np.arange(len(plot_df))
    bottom = np.zeros(len(plot_df))
    colors = {
        "C_disp": "#4C78A8",
        "C_norm": "#F58518",
        "C_peak": "#54A24B",
        "C_region": "#E45756",
        "C_weak": "#B279A2",
    }

    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    for component in stable.COST_COMPONENTS:
        values = plot_df[f"weighted_{component}"].to_numpy(dtype=float)
        ax.bar(x, values, bottom=bottom, label=f"{WEIGHTS[component]:.2f} {stable.COST_COMPONENT_LABELS[component]}", color=colors[component])
        bottom += values

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel("Prompt condition")
    ax.set_ylabel(r"Weighted contribution to $\mathit{J}_{\mathit{stable}}$")
    ax.set_title("Round 2 Weighted Cost Contributions")
    ax.legend(loc="upper right", frameon=True, fontsize=8)
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.8, alpha=0.8)
    fig.tight_layout()
    fig.savefig(output_dir / "round2_weighted_component_contributions.png", dpi=300)
    plt.close(fig)


def write_report(
    response_df: pd.DataFrame,
    log_df: pd.DataFrame,
    cost_df: pd.DataFrame,
    component_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    best = cost_df.iloc[0]
    compact = cost_df[
        [
            "rank",
            "prompt_id",
            "prompt_type",
            "N",
            "mean_D1",
            "mean_D2",
            "mean_D3",
            "P_omega",
            "C_disp",
            "C_norm",
            "C_peak",
            "C_region",
            "C_weak",
            "J_stable",
            "main_problem",
            "second_problem",
        ]
    ].copy()
    for column in [
        "mean_D1",
        "mean_D2",
        "mean_D3",
        "P_omega",
        "C_disp",
        "C_norm",
        "C_peak",
        "C_region",
        "C_weak",
        "J_stable",
    ]:
        compact[column] = compact[column].map(lambda value: f"{value:.4f}")

    components = component_df[
        [
            "prompt_id",
            "weighted_C_disp",
            "weighted_C_norm",
            "weighted_C_peak",
            "weighted_C_region",
            "weighted_C_weak",
            "J_stable",
        ]
    ].copy()
    for column in components.columns:
        if column != "prompt_id":
            components[column] = components[column].map(lambda value: f"{value:.4f}")

    report = f"""# Round 2 Stable-Cost Component Analysis

## Data overview

This analysis used {len(response_df)} scored responses from {len(cost_df)} prompt conditions in `round2/`.

{stable.dataframe_to_markdown(log_df)}

## Formula

`J_stable(P) = 0.20*C_disp + 0.20*C_norm + 0.20*C_peak + 0.20*C_region + 0.20*C_weak`.

`C_disp` uses the root-mean-square normalized distance from each response to its prompt-level mean point.

## Prompt ranking

{stable.dataframe_to_markdown(compact)}

## Weighted component contributions

{stable.dataframe_to_markdown(components)}

## Interpretation

The lowest-cost prompt in this round is **{best['prompt_id']} ({best['prompt_type']})**, with `J_stable = {best['J_stable']:.4f}`.

The new score-only file `PHYSICS-R2-C3-score.csv` was mapped as `Score -> D1`, `score2 -> D2`, and `Score_3 -> D3`. The original `qwen-prompt1-3.csv` and `qwen-prompt1-7.csv` files were used directly and labeled as `R1-C3` and `R1-C7`.

Because this analysis compares only scored dimensions, inspect response text separately before concluding that a very low dispersion result is substantively better. Low dispersion can also reflect overly templated answers.
"""
    (output_dir / "round2_stable_iteration_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    response_df, log_df = load_round2_data(ROUND2_DIR)
    cost_df = stable.compute_all_stable_costs(response_df)
    component_df = build_component_contributions(cost_df)

    save_round2_tables(response_df, log_df, cost_df, component_df, OUTPUT_DIR)
    write_report(response_df, log_df, cost_df, component_df, OUTPUT_DIR)
    plot_total_cost(cost_df, OUTPUT_DIR)
    plot_component_heatmap(cost_df, OUTPUT_DIR)
    plot_dimension_means(cost_df, OUTPUT_DIR)
    plot_weighted_contributions(component_df, OUTPUT_DIR)

    print(f"Loaded {len(response_df)} scored responses from {len(cost_df)} prompt conditions.")
    print(f"Best prompt: {cost_df.iloc[0]['prompt_id']} ({cost_df.iloc[0]['prompt_type']})")
    print(f"Lowest J_stable: {cost_df.iloc[0]['J_stable']:.4f}")
    print(f"Outputs saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
