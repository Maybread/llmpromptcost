from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["svg.fonttype"] = "none"

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd


INPUT_CSV = Path("outputs/stable_cost_prompt_iteration/stable_cost_summary.csv")
OUTPUT_DIR = INPUT_CSV.parent
OUTPUT_PNG = OUTPUT_DIR / "stability_normativity_tradeoff.png"
OUTPUT_SVG = OUTPUT_DIR / "stability_normativity_tradeoff.svg"


def condition_label(prompt_id: str) -> str:
    if str(prompt_id).startswith("R1-P"):
        return str(prompt_id)
    match = re.search(r"(\d+)", str(prompt_id))
    return f"R1-P{match.group(1)}" if match else str(prompt_id)


def condition_number(prompt_id: str) -> int:
    match = re.search(r"(?:P|C)(\d+)$", str(prompt_id), flags=re.IGNORECASE)
    if not match:
        match = re.search(r"(\d+)", str(prompt_id))
    return int(match.group(1)) if match else 9999


def main() -> None:
    df = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
    df["condition_label"] = df["prompt_id"].map(condition_label)
    df["condition_number"] = df["prompt_id"].map(condition_number)
    df = df.sort_values("condition_number").reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(9.8, 6.0))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    x_min = max(0.0, df["C_disp"].min() - 0.012)
    x_max = df["C_disp"].max() + 0.018
    y_min = 0.0
    y_max = min(1.0, df["P_omega"].max() + 0.09)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

    # The upper-left region is ideal: lower conceptual dispersion cost and
    # higher normative-region proportion.
    ideal_width = max(0.001, (df["C_disp"].quantile(0.40) - x_min))
    ideal_height = max(0.001, y_max - df["P_omega"].quantile(0.65))
    ax.add_patch(
        Rectangle(
            (x_min, y_max - ideal_height),
            ideal_width,
            ideal_height,
            facecolor="#d9ead3",
            edgecolor="none",
            alpha=0.45,
            zorder=0,
        )
    )

    ax.annotate(
        "Low dispersion & high normative proportion",
        xy=(x_min + 0.004, y_max - 0.055),
        color="#31572c",
        fontsize=9.5,
        ha="left",
        va="center",
    )
    colors = {
        "R1-P3": "#1f4e79",
        "R1-P7": "#8b1a1a",
        "R1-P2": "#777777",
        "R1-P4": "#777777",
    }
    markers = {
        "R1-P3": "o",
        "R1-P7": "^",
        "R1-P2": "o",
        "R1-P4": "o",
    }
    sizes = {
        "R1-P3": 170,
        "R1-P7": 190,
        "R1-P2": 95,
        "R1-P4": 95,
    }

    # Plot each prompt condition in the stability-normativity plane:
    # x-axis = C_disp, a stability cost where lower is better;
    # y-axis = P_omega, a normative-region proportion where higher is better.
    for _, row in df.iterrows():
        label = row["condition_label"]
        if label in {"R1-P3", "R1-P7", "R1-P2", "R1-P4"}:
            color = colors[label]
            marker = markers[label]
            size = sizes[label]
            alpha = 0.96
            edgecolor = "black"
            linewidth = 0.9
        else:
            color = "#c9c9c9"
            marker = "o"
            size = 80
            alpha = 0.82
            edgecolor = "#888888"
            linewidth = 0.5

        ax.scatter(
            row["C_disp"],
            row["P_omega"],
            s=size,
            marker=marker,
            color=color,
            alpha=alpha,
            edgecolors=edgecolor,
            linewidths=linewidth,
            zorder=3,
        )

    row_p3 = df[df["condition_label"] == "R1-P3"].iloc[0]
    row_p7 = df[df["condition_label"] == "R1-P7"].iloc[0]
    ax.plot(
        [row_p7["C_disp"], row_p3["C_disp"]],
        [row_p7["P_omega"], row_p3["P_omega"]],
        linestyle="--",
        color="#444444",
        linewidth=1.25,
        zorder=2,
    )
    mid_x = (row_p7["C_disp"] + row_p3["C_disp"]) / 2
    mid_y = (row_p7["P_omega"] + row_p3["P_omega"]) / 2
    ax.annotate(
        "Complementary targets",
        xy=(mid_x, mid_y),
        xytext=(mid_x + 0.012, mid_y - 0.040),
        arrowprops=dict(arrowstyle="-", color="#444444", lw=0.8),
        fontsize=9.5,
        color="#333333",
        ha="left",
        va="center",
    )

    offsets = {
        "R1-P1": (-16, 8),
        "R1-P2": (8, 8),
        "R1-P3": (14, 0),
        "R1-P4": (8, -16),
        "R1-P5": (8, -16),
        "R1-P6": (8, 8),
        "R1-P7": (10, -18),
    }
    label_texts = {
        "R1-P3": "R1-P3: normative baseline",
        "R1-P7": "R1-P7: stability baseline",
    }

    for _, row in df.iterrows():
        label = row["condition_label"]
        text = label_texts.get(label, label)
        dx, dy = offsets.get(label, (6, 6))
        ax.annotate(
            text,
            xy=(row["C_disp"], row["P_omega"]),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=9.5 if label in {"R1-P3", "R1-P7"} else 9,
            fontweight="bold" if label in {"R1-P3", "R1-P7"} else "normal",
            color="#222222" if label in {"R1-P3", "R1-P7"} else "#555555",
            ha="left",
            va="center",
            zorder=4,
        )

    ax.set_title("Stability\u2013Normativity Trade-off Across Prompt Conditions", fontsize=14, pad=14)
    ax.set_xlabel(r"Conceptual dispersion cost $\mathit{C}_{\mathit{disp}}$", fontsize=11)
    ax.set_ylabel(r"Normative-region proportion $P_{\Omega}$", fontsize=11)
    ax.grid(True, color="#d9d9d9", linewidth=0.8, alpha=0.8)
    ax.set_axisbelow(True)

    legend_handles = [
        ax.scatter([], [], s=170, marker="o", color=colors["R1-P3"], edgecolors="black", label="R1-P3"),
        ax.scatter([], [], s=190, marker="^", color=colors["R1-P7"], edgecolors="black", label="R1-P7"),
        ax.scatter([], [], s=95, marker="o", color="#777777", edgecolors="black", label="R1-P2/R1-P4"),
        ax.scatter([], [], s=80, marker="o", color="#c9c9c9", edgecolors="#888888", label="Other"),
    ]
    ax.legend(
        handles=legend_handles,
        loc="upper right",
        frameon=True,
        facecolor="white",
        framealpha=0.92,
    )

    fig.tight_layout()
    fig.savefig(OUTPUT_PNG, dpi=300)
    fig.savefig(OUTPUT_SVG, dpi=300)
    plt.close(fig)
    print(f"Saved {OUTPUT_PNG}")
    print(f"Saved {OUTPUT_SVG}")


if __name__ == "__main__":
    main()
