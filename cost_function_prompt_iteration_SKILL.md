# Cost-Function-Guided Prompt Iteration Skill

## Purpose

Use this skill to conduct cost-function-guided iterative prompt optimization for AI-generated scientific explanations.

This skill is designed for studies where several prompt conditions have already been tested and the generated responses have been scored along three conceptual dimensions:

- D1: core concept / energy transformation
- D2: conditional model / ideal vs. real situation distinction
- D3: terminology use / scientific expression

The goal is to compute a multidimensional prompt-level cost function, diagnose the remaining problems of the best prompts, and generate the next-round prompt candidates based on the actual first-round results.

This skill does not train or fine-tune the model. It treats each prompt as a candidate configuration and evaluates the distribution of responses induced by that prompt.

---

## When to Use This Skill

Use this skill when the user wants to:

- evaluate several prompt conditions using a cost function;
- compare baseline, role, component, stepwise, self-check, or integrated prompts;
- identify the best-performing prompt based on multidimensional cost;
- diagnose why a prompt is still suboptimal;
- generate second-round or later-round prompt candidates based on cost-function results;
- build a reproducible iterative prompt optimization workflow.

Do not use this skill if:

- there are no D1/D2/D3 scores available;
- the user wants to fine-tune model parameters;
- the user wants to optimize prompts without any response-level evaluation data;
- the user asks for purely theoretical explanation without data processing.

---

## Core Principle

The next-round prompt must not be predetermined before the current-round cost values are computed.

The correct workflow is:

```text
Current-round prompt results
        ↓
Compute five cost components
        ↓
Rank prompts by total cost
        ↓
Select top 1–2 prompts
        ↓
Diagnose the main remaining cost problem
        ↓
Apply prompt revision strategy
        ↓
Generate next-round prompt candidates
```

Do not generate second-round prompts directly from templates before seeing first-round results.

Prompt revision templates are only a strategy library, not final prompts.

---

## Required Input Data

The input file should be a `.csv` or `.xlsx` file containing response-level results.

Required columns:

```text
prompt_id
prompt_type
response_id
response_text
D1
D2
D3
```

Acceptable alternative column names:

```text
condition, prompt, prompt_name, Prompt 类型 -> prompt_id or prompt_type
dim1, DIM1, core_concept -> D1
dim2, DIM2, condition_model -> D2
dim3, DIM3, terminology -> D3
answer, response, output -> response_text
```

If required columns cannot be identified, stop and report the missing columns.

---

## Data Preprocessing

### 1. Preserve Original Data

Never overwrite the original data file.

All processed files must be saved to a new output directory:

```text
outputs/cost_function_iteration/
```

### 2. Normalize Scores

Check whether D1, D2, and D3 are already in the range `[0, 1]`.

If scores are in the range `[0, 2]`, convert them as:

```text
0 -> 0
1 -> 0.5
2 -> 1
```

If scores are already in `[0, 1]`, keep them unchanged.

If missing values exist in D1/D2/D3, remove those rows and report the number of removed responses.

---

## Target Point and Normative Region

Define the target conceptual point as:

```text
v* = (0.80, 1.00, 1.00)
```

Rationale:

- D1 is expected to reach a high level, but it does not need to be exactly full score.
- D2 and D3 are expected to reach complete and normative levels.
- The goal is not to maximize a single dimension, but to move the response distribution into a high-quality conceptual region.

Define the normative region as:

```text
Omega = {x | D1 >= 0.80, D2 >= 0.80, D3 >= 0.80}
```

A response is considered to be in the normative region only if all three dimensions meet the threshold.

---

## Cost Function Definition

For a prompt `P`, suppose it generates `N` responses.

Each response is represented as:

```text
x_i = (D1_i, D2_i, D3_i)
```

The total prompt-level cost is:

```text
J(P) = 0.30*C_norm
     + 0.25*C_peak
     + 0.20*C_region
     + 0.15*C_weak
     + 0.10*C_disp
```

A lower `J(P)` indicates a better prompt.

---

## Cost Component 1: C_norm

### Meaning

`C_norm` measures the average distance between all generated responses and the target conceptual point.

### Formula

```text
C_norm = mean( ||x_i - v*||_2 / sqrt(3) )
```

### Interpretation

A lower `C_norm` means the prompt generates responses that are overall closer to the scientific normative target.

---

## Cost Component 2: C_peak

### Meaning

`C_peak` measures the distance between the density peak and the target point.

The density peak is the most frequent D1-D2-D3 score combination under a prompt.

### Formula

```text
p_peak = most frequent score vector under prompt P
C_peak = ||p_peak - v*||_2 / sqrt(3)
```

### Interpretation

A lower `C_peak` means the most common response type is closer to the high-quality conceptual region.

This is important because a prompt is not good enough if it only occasionally generates high-quality responses. Its most frequent response pattern should also be high quality.

---

## Cost Component 3: C_region

### Meaning

`C_region` measures the proportion of responses that fail to enter the normative region.

### Formula

```text
P_omega = number_of_responses_in_Omega / N
C_region = 1 - P_omega
```

### Interpretation

A lower `C_region` means a larger proportion of responses enter the high-quality region.

---

## Cost Component 4: C_weak

### Meaning

`C_weak` penalizes dimension-level weaknesses.

### Formula

Let:

```text
theta = (0.80, 0.80, 0.80)
mean_D = (mean_D1, mean_D2, mean_D3)
```

Then:

```text
C_weak = [max(0, 0.80 - mean_D1)
        + max(0, 0.80 - mean_D2)
        + max(0, 0.80 - mean_D3)] / 3
```

### Interpretation

A lower `C_weak` means the prompt does not leave any dimension substantially underdeveloped.

If `C_weak` is high, identify the lowest mean dimension:

```text
lowest mean_D1 -> D1 weakness
lowest mean_D2 -> D2 weakness
lowest mean_D3 -> D3 weakness
```

---

## Cost Component 5: C_disp

### Meaning

`C_disp` measures the conceptual dispersion of responses under the same prompt.

### Formula

Let:

```text
mu = (mean_D1, mean_D2, mean_D3)
```

Then:

```text
C_disp = mean( ||x_i - mu||_2 / sqrt(3) )
```

### Interpretation

A lower `C_disp` means the prompt generates more stable responses.

However, do not assume dispersion should always be minimized. Very low dispersion may suggest over-template responses. If this occurs, mention it as a possible side effect in the report.

---

## Main Analysis Workflow

### Step 1: Load Current-Round Results

Read the current-round prompt results file.

Validate required columns.

Normalize D1/D2/D3 if necessary.

---

### Step 2: Compute Cost for Each Prompt

For every prompt condition, calculate:

```text
N
mean_D1
mean_D2
mean_D3
p_peak_D1
p_peak_D2
p_peak_D3
P_omega
C_norm
C_peak
C_region
C_weak
C_disp
J_total
```

---

### Step 3: Rank Prompts

Sort prompts by `J_total` in ascending order.

The prompt with the lowest `J_total` is the current best prompt.

If multiple prompts have very similar `J_total`, report this and recommend bootstrap confidence intervals or a larger sample size.

---

### Step 4: Diagnose Each Prompt

For each prompt, identify the largest cost component among:

```text
C_norm
C_peak
C_region
C_weak
C_disp
```

Use the following diagnostic rules:

| Highest Cost Component | Diagnosis | Revision Direction |
|---|---|---|
| C_norm | Overall normative distance is high | Strengthen scientific completeness and normative explanation |
| C_peak | Density peak is not in the desired region | Clarify the components of a high-quality explanation |
| C_region | Too few responses enter the normative region | Set minimum required explanation components |
| C_weak | One dimension is underdeveloped | Repair the weakest D1/D2/D3 dimension |
| C_disp | Responses are too dispersed | Add explanation order and coherence constraints |

---

## Selecting Prompts for Next-Round Revision

Select the top 1–2 prompts with the lowest `J_total`.

Do not select prompts only by mean score.

A prompt can have a high average score but still be suboptimal if:

- its density peak is far from the target;
- its normative-region proportion is low;
- it has one weak dimension;
- its response distribution is too dispersed.

---

## Generating Next-Round Prompts

### Fundamental Rule

Next-round prompts must be generated from the selected current-round best prompts.

Do not generate unrelated new prompts from scratch unless the current prompt pool has completely failed.

### For Each Selected Prompt

Generate 3–5 variants:

1. A variant targeting the highest cost component.
2. A variant targeting the second-highest cost component.
3. A variant combining repairs for the highest two cost components.
4. A compressed variant to avoid excessive prompt length.
5. A natural-expression variant to reduce over-template risk.

For each generated prompt, explain:

```text
source_prompt_id
source_prompt_text
target_cost_component
diagnosed_problem
revision_operation
expected_effect
possible_side_effect
next_round_prompt
```

---

## Prompt Revision Strategy Library

This section provides strategy rules. These are not final prompts. Use them only after cost results are computed.

### If C_norm Is High

Problem:

```text
Responses are generally far from the scientific normative target.
```

Revision strategy:

```text
Add requirements for complete scientific explanation, including energy change, scientific principle, applicable conditions, and terminology.
```

Possible wording:

```text
请从能量角度解释这一科学现象。你的解释应清楚说明相关能量如何发生变化，并说明这种变化背后的科学原理；在必要时指出解释成立的条件，并使用恰当的科学术语。
```

---

### If C_peak Is High

Problem:

```text
The most frequent response type is not sufficiently high quality.
```

Revision strategy:

```text
Make the components of a complete explanation explicit, so that the most common answer pattern moves toward the normative region.
```

Possible wording:

```text
请从能量角度解释这一科学现象。一个完整的解释应包括：能量变化过程、该过程成立的条件，以及关键科学术语的准确使用。请将这些内容组织成一段连贯解释。
```

---

### If C_region Is High

Problem:

```text
The proportion of responses entering the normative region is too low.
```

Revision strategy:

```text
Set minimum answer requirements.
```

Possible wording:

```text
请从能量角度解释这一科学现象。回答中至少应包含三个方面：相关能量如何变化、解释这一变化时需要考虑的条件，以及恰当使用科学术语。请避免只给出笼统描述。
```

---

### If C_weak Is High

First identify the weakest dimension.

#### If D1 Is Weak

Problem:

```text
Core concept or energy transformation is insufficient.
```

Possible wording:

```text
请从能量角度解释这一科学现象。请重点说明初始状态、过程中能量形式的变化，以及这些能量变化之间的关系。必要时说明相关条件，并使用恰当科学术语。
```

#### If D2 Is Weak

Problem:

```text
Conditional model is insufficient.
```

Possible wording:

```text
请从能量角度解释这一科学现象。除说明能量变化外，还要明确指出该解释在什么条件下成立；如果理想情况和真实情况中的能量变化不同，请分别说明。请使用恰当科学术语。
```

#### If D3 Is Weak

Problem:

```text
Scientific terminology is insufficient.
```

Possible wording:

```text
请从能量角度解释这一科学现象。请在说明能量变化和相关条件的同时，使用准确的科学术语表达，不要只使用日常化或模糊表述。
```

---

### If C_disp Is High

Problem:

```text
Responses are too dispersed.
```

Revision strategy:

```text
Add explanation order, structure, and coherence constraints.
```

Possible wording:

```text
请从能量角度解释这一科学现象。请按照“初始状态—能量变化过程—需要考虑的条件—科学术语总结”的顺序进行连贯解释，避免遗漏关键环节。
```

---

## Output Requirements

Save all outputs to:

```text
outputs/cost_function_iteration/
```

Required output files:

### 1. cost_summary.csv

Must include:

```text
prompt_id
prompt_type
N
mean_D1
mean_D2
mean_D3
p_peak_D1
p_peak_D2
p_peak_D3
P_omega
C_norm
C_peak
C_region
C_weak
C_disp
J_total
rank
main_problem
suggested_revision_direction
```

### 2. cost_summary.xlsx

Same content as `cost_summary.csv`, formatted for manual review.

### 3. iteration_report.md

Must include:

```text
1. Data overview
2. Score normalization method
3. Cost function definition
4. Cost summary and prompt ranking
5. Current best prompt
6. Diagnostic interpretation of cost components
7. Why the best prompt is selected by total cost rather than average score
8. Remaining problems of the best prompt
9. Next-round prompt generation logic
10. Next-round prompt candidates
11. Potential risks, including over-template responses
12. Recommended next experiment
```

### 4. next_round_prompts.md

Must include only the next-round prompt candidates and their diagnostic basis.

### 5. total_cost_barplot.png

Bar plot of `J_total` by prompt.

### 6. cost_components_heatmap.png

Heatmap of the five cost components by prompt.

### 7. dimension_means_barplot.png

Bar plot comparing `mean_D1`, `mean_D2`, and `mean_D3`.

---

## Visualization Rules

Use English labels in figures to avoid font issues:

```text
Prompt
Mean D1
Mean D2
Mean D3
Total Cost
C_norm
C_peak
C_region
C_weak
C_disp
```

Keep figures simple and suitable for academic drafts.

---

## Suggested Python Functions

Implement at least the following functions:

```python
load_experiment_data(path)
standardize_columns(df)
normalize_scores(df)
compute_prompt_cost(df_prompt)
compute_all_prompt_costs(df)
diagnose_prompt(row)
select_prompts_for_revision(cost_df, top_k=2)
generate_next_round_prompts(best_rows)
save_outputs(cost_df, prompts, output_dir)
plot_total_cost(cost_df, output_dir)
plot_cost_components(cost_df, output_dir)
plot_dimension_means(cost_df, output_dir)
```

---

## Pseudocode

```python
def compute_prompt_cost(df_prompt):
    X = df_prompt[["D1", "D2", "D3"]].to_numpy()
    N = len(X)

    v_star = np.array([0.80, 1.00, 1.00])
    theta = np.array([0.80, 0.80, 0.80])

    mu = X.mean(axis=0)

    C_norm = np.mean(np.linalg.norm(X - v_star, axis=1) / np.sqrt(3))

    peak_counts = (
        df_prompt.groupby(["D1", "D2", "D3"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    p_peak = peak_counts.iloc[0][["D1", "D2", "D3"]].to_numpy(dtype=float)
    C_peak = np.linalg.norm(p_peak - v_star) / np.sqrt(3)

    in_omega = (
        (df_prompt["D1"] >= 0.80)
        & (df_prompt["D2"] >= 0.80)
        & (df_prompt["D3"] >= 0.80)
    )
    P_omega = in_omega.mean()
    C_region = 1 - P_omega

    C_weak = np.mean(np.maximum(0, theta - mu))

    C_disp = np.mean(np.linalg.norm(X - mu, axis=1) / np.sqrt(3))

    J_total = (
        0.30 * C_norm
        + 0.25 * C_peak
        + 0.20 * C_region
        + 0.15 * C_weak
        + 0.10 * C_disp
    )

    return {
        "N": N,
        "mean_D1": mu[0],
        "mean_D2": mu[1],
        "mean_D3": mu[2],
        "p_peak_D1": p_peak[0],
        "p_peak_D2": p_peak[1],
        "p_peak_D3": p_peak[2],
        "P_omega": P_omega,
        "C_norm": C_norm,
        "C_peak": C_peak,
        "C_region": C_region,
        "C_weak": C_weak,
        "C_disp": C_disp,
        "J_total": J_total,
    }
```

---

## Reporting Style

When writing the report, avoid saying:

```text
Prompt X is best because it has the highest average score.
```

Instead write:

```text
Prompt X has the lowest total cost, indicating that it provides the best overall balance among normative proximity, density peak location, normative-region proportion, dimensional weakness, and conceptual dispersion.
```

If a prompt has a high average score but high cost, explain why:

```text
Although this prompt has a relatively high mean score, its cost remains high because its density peak is not located in the normative region and its D2 dimension remains weak.
```

---

## Important Cautions

1. Do not predefine the next-round prompts before current-round cost values are computed.
2. Do not optimize only for mean score.
3. Do not assume lower dispersion is always better; very low dispersion may indicate response homogenization.
4. Do not overwrite raw data.
5. Do not use prompt templates mechanically. Always tie prompt revision to actual cost diagnosis.
6. Do not claim full automatic prompt optimization unless prompt generation and selection are fully automated.
7. Use the phrase `cost-function-guided iterative prompt optimization` for English writing.
8. Use the phrase `成本函数引导的提示词迭代优化` for Chinese writing.

---

## Final Deliverable Goal

After this skill is executed, the user should have:

1. A ranked table of current-round prompts by total cost.
2. A diagnosis of why each prompt performs well or poorly.
3. Identification of the current best prompt.
4. A data-driven set of next-round prompt candidates.
5. Visualizations for total cost, cost components, and dimension means.
6. A reproducible report explaining how the next round is generated from the current cost results.

# prompt 类型
Condition 1	Baseline open prompt
Condition 2	Role prompt
Condition 3	Task-component prompt
Condition 4	Reasoning scaffold prompt
Condition 5	Knowledge-grounded prompt（RAG）
Condition 6	Self-checking prompt
condition 7	Demonstration prompt
