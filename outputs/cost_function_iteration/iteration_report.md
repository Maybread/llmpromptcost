# Cost-Function-Guided Prompt Iteration Report

## 1. Data overview

The analysis used 3500 response-level scored records across 7 prompt conditions.
Files were loaded from `round1/`. Condition 1 is a score-only file; its `response_text` was not available, so it was retained for cost computation with an empty response-text field.

## 2. Score normalization method

Scores were standardized into the [0, 1] interval before cost computation. Rows with missing D1/D2/D3 values were removed if present.

| source_file        | prompt_id   | encoding  | original_rows | retained_rows | normalization_method     | notes                                                                |
| ------------------ | ----------- | --------- | ------------- | ------------- | ------------------------ | -------------------------------------------------------------------- |
| qwen-prompt1-1.csv | Condition 1 | utf-8-sig | 500           | 500           | scores already in [0, 1] | response_text missing; filled with empty string for cost computation |
| qwen-prompt1-2.csv | Condition 2 | gb18030   | 500           | 500           | scores already in [0, 1] |                                                                      |
| qwen-prompt1-3.csv | Condition 3 | gb18030   | 500           | 500           | scores already in [0, 1] |                                                                      |
| qwen-prompt1-4.csv | Condition 4 | gb18030   | 500           | 500           | scores already in [0, 1] |                                                                      |
| qwen-prompt1-5.csv | Condition 5 | gb18030   | 500           | 500           | scores already in [0, 1] |                                                                      |
| qwen-prompt1-6.csv | Condition 6 | gb18030   | 500           | 500           | scores already in [0, 1] |                                                                      |
| qwen-prompt1-7.csv | Condition 7 | gb18030   | 500           | 500           | scores already in [0, 1] |                                                                      |

## 3. Cost function definition

The target conceptual point is `v* = (0.80, 1.00, 1.00)`. The normative region is `Omega = {x | D1 >= 0.80, D2 >= 0.80, D3 >= 0.80}`.

`J(P) = 0.30*C_norm + 0.25*C_peak + 0.20*C_region + 0.15*C_weak + 0.10*C_disp`.

Lower total cost indicates a better balance among normative proximity, density peak location, normative-region proportion, dimensional weakness, and conceptual dispersion.

## 4. Cost summary and prompt ranking

| rank | prompt_id   | prompt_type                     | N   | mean_D1 | mean_D2 | mean_D3 | P_omega | J_total | main_problem                                           |
| ---- | ----------- | ------------------------------- | --- | ------- | ------- | ------- | ------- | ------- | ------------------------------------------------------ |
| 1    | Condition 7 | Demonstration prompt            | 500 | 0.7672  | 1.0000  | 0.9848  | 0.6500  | 0.0990  | C_region: Too few responses enter the normative region |
| 2    | Condition 3 | Task-component prompt           | 500 | 0.8516  | 0.9980  | 0.9820  | 0.7220  | 0.1237  | C_region: Too few responses enter the normative region |
| 3    | Condition 2 | Role prompt                     | 500 | 0.8136  | 0.9868  | 0.7944  | 0.6420  | 0.1255  | C_region: Too few responses enter the normative region |
| 4    | Condition 4 | Reasoning scaffold prompt       | 500 | 0.9132  | 0.9996  | 0.8156  | 0.5220  | 0.1890  | C_region: Too few responses enter the normative region |
| 5    | Condition 1 | Baseline open prompt            | 500 | 0.7284  | 0.9944  | 0.7080  | 0.2620  | 0.2735  | C_region: Too few responses enter the normative region |
| 6    | Condition 5 | Knowledge-grounded prompt (RAG) | 500 | 0.4784  | 1.0000  | 0.9876  | 0.1800  | 0.3029  | C_region: Too few responses enter the normative region |
| 7    | Condition 6 | Self-checking prompt            | 500 | 0.3928  | 0.9604  | 0.9992  | 0.0200  | 0.3561  | C_region: Too few responses enter the normative region |

The current ranking has a visible separation between the best prompt and the next prompt.

## 5. Current best prompt

The current best prompt is **Condition 7 (Demonstration prompt)** with the lowest total cost, `J_total = 0.0990`.

## 6. Diagnostic interpretation of cost components

For each prompt, the largest remaining cost component was used as the main diagnostic signal. `C_region` indicates insufficient entry into the normative region, `C_peak` indicates that the most frequent response type remains below target, `C_norm` captures overall distance from the target point, `C_weak` marks a weak dimension, and `C_disp` captures response dispersion.

## 7. Why the best prompt is selected by total cost rather than average score

The best prompt is not selected because it has the highest average score. It is selected because it has the lowest total cost, indicating the best overall balance among normative proximity, density peak location, normative-region proportion, dimensional weakness, and conceptual dispersion.

## 8. Remaining problems of the best prompt

The main remaining problem for Condition 7 is: **C_region: Too few responses enter the normative region**. Its recommended revision direction is: **Set minimum required explanation components**.

## 9. Next-round prompt generation logic

The next-round prompt candidates were generated from the top 1-2 prompts ranked by total cost. For each selected prompt, variants target the largest cost component, the second-largest cost component, a combined repair, a compressed version, and a natural-expression version to reduce over-template risk.

## 10. Next-round prompt candidates

### Condition 7_v1

- source_prompt_id: Condition 7
- source_prompt_text: Original prompt text was not provided in the input files; available source condition is Demonstration prompt.
- target_cost_component: C_region
- diagnosed_problem: C_region: Too few responses enter the normative region
- revision_operation: set minimum answer requirements
- expected_effect: a larger proportion of responses should enter the normative region
- possible_side_effect: minimum requirements may reduce stylistic diversity

```text
请从能量角度解释石块从高空落下这一现象。回答中至少应包含三个方面：相关能量如何变化、解释这一变化时需要考虑的条件，以及恰当使用科学术语。请避免只给出笼统描述。
```

### Condition 7_v2

- source_prompt_id: Condition 7
- source_prompt_text: Original prompt text was not provided in the input files; available source condition is Demonstration prompt.
- target_cost_component: C_disp
- diagnosed_problem: C_disp: Responses are too dispersed
- revision_operation: add explanation order and coherence constraints
- expected_effect: responses should become more stable and coherent
- possible_side_effect: too much structure may create over-template responses

```text
请从能量角度解释石块从高空落下这一现象。请按照“初始状态、能量变化过程、需要考虑的条件、科学术语总结”的顺序进行连贯解释，避免遗漏关键环节。
```

### Condition 7_v3

- source_prompt_id: Condition 7
- source_prompt_text: Original prompt text was not provided in the input files; available source condition is Demonstration prompt.
- target_cost_component: C_region + C_disp
- diagnosed_problem: C_region: Too few responses enter the normative region; C_disp: Responses are too dispersed
- revision_operation: combine set minimum answer requirements and add explanation order and coherence constraints
- expected_effect: the answer distribution should improve on the two largest remaining cost sources
- possible_side_effect: combined constraints may increase prompt length

```text
请从能量角度解释石块从高空落下这一现象。请用一段连贯文字完成解释，并同时满足以下要求：第一，至少包含能量如何变化、需要考虑的条件、恰当科学术语三个方面。第二，按照初始状态、能量变化过程、条件、术语总结的顺序连贯解释。请避免只给出笼统结论。
```

### Condition 7_v4

- source_prompt_id: Condition 7
- source_prompt_text: Original prompt text was not provided in the input files; available source condition is Demonstration prompt.
- target_cost_component: C_region
- diagnosed_problem: C_region: Too few responses enter the normative region
- revision_operation: compress the highest-component repair into a shorter instruction
- expected_effect: retain the main repair while reducing prompt length
- possible_side_effect: shorter wording may provide weaker guidance

```text
请从能量角度解释石块从高空落下，简洁说明能量变化、成立条件和关键科学术语，避免笼统描述。
```

### Condition 7_v5

- source_prompt_id: Condition 7
- source_prompt_text: Original prompt text was not provided in the input files; available source condition is Demonstration prompt.
- target_cost_component: C_region + over-template risk
- diagnosed_problem: C_region: Too few responses enter the normative region; possible over-template risk
- revision_operation: make the repair sound more natural and less template-like
- expected_effect: reduce response homogenization while keeping cost-guided requirements
- possible_side_effect: less rigid structure may slightly increase dispersion

```text
请像给学生讲解一样，从能量角度说明石块为什么会从高空落下。讲清楚能量从哪里来、如何变化、哪些条件会影响解释，并自然地使用准确科学术语。
```

### Condition 3_v1

- source_prompt_id: Condition 3
- source_prompt_text: Original prompt text was not provided in the input files; available source condition is Task-component prompt.
- target_cost_component: C_region
- diagnosed_problem: C_region: Too few responses enter the normative region
- revision_operation: set minimum answer requirements
- expected_effect: a larger proportion of responses should enter the normative region
- possible_side_effect: minimum requirements may reduce stylistic diversity

```text
请从能量角度解释石块从高空落下这一现象。回答中至少应包含三个方面：相关能量如何变化、解释这一变化时需要考虑的条件，以及恰当使用科学术语。请避免只给出笼统描述。
```

### Condition 3_v2

- source_prompt_id: Condition 3
- source_prompt_text: Original prompt text was not provided in the input files; available source condition is Task-component prompt.
- target_cost_component: C_peak
- diagnosed_problem: C_peak: Density peak is not in the desired region
- revision_operation: make the components of a complete explanation explicit
- expected_effect: the most frequent answer pattern should move toward the normative region
- possible_side_effect: answers may become more uniform

```text
请从能量角度解释石块从高空落下这一现象。一个完整的解释应包括：能量变化过程、该过程成立的条件，以及关键科学术语的准确使用。请将这些内容组织成一段连贯解释。
```

### Condition 3_v3

- source_prompt_id: Condition 3
- source_prompt_text: Original prompt text was not provided in the input files; available source condition is Task-component prompt.
- target_cost_component: C_region + C_peak
- diagnosed_problem: C_region: Too few responses enter the normative region; C_peak: Density peak is not in the desired region
- revision_operation: combine set minimum answer requirements and make the components of a complete explanation explicit
- expected_effect: the answer distribution should improve on the two largest remaining cost sources
- possible_side_effect: combined constraints may increase prompt length

```text
请从能量角度解释石块从高空落下这一现象。请用一段连贯文字完成解释，并同时满足以下要求：第一，至少包含能量如何变化、需要考虑的条件、恰当科学术语三个方面。第二，明确包含能量变化过程、成立条件和关键科学术语，使常见回答模式更完整。请避免只给出笼统结论。
```

### Condition 3_v4

- source_prompt_id: Condition 3
- source_prompt_text: Original prompt text was not provided in the input files; available source condition is Task-component prompt.
- target_cost_component: C_region
- diagnosed_problem: C_region: Too few responses enter the normative region
- revision_operation: compress the highest-component repair into a shorter instruction
- expected_effect: retain the main repair while reducing prompt length
- possible_side_effect: shorter wording may provide weaker guidance

```text
请从能量角度解释石块从高空落下，简洁说明能量变化、成立条件和关键科学术语，避免笼统描述。
```

### Condition 3_v5

- source_prompt_id: Condition 3
- source_prompt_text: Original prompt text was not provided in the input files; available source condition is Task-component prompt.
- target_cost_component: C_region + over-template risk
- diagnosed_problem: C_region: Too few responses enter the normative region; possible over-template risk
- revision_operation: make the repair sound more natural and less template-like
- expected_effect: reduce response homogenization while keeping cost-guided requirements
- possible_side_effect: less rigid structure may slightly increase dispersion

```text
请像给学生讲解一样，从能量角度说明石块为什么会从高空落下。讲清楚能量从哪里来、如何变化、哪些条件会影响解释，并自然地使用准确科学术语。
```

## 11. Potential risks, including over-template responses

Very low dispersion can indicate response homogenization. Some next-round candidates deliberately add structure, which may reduce dispersion but can also make answers too template-like. The natural-expression variants are included to test whether conceptual quality can improve without excessive standardization.

## 12. Recommended next experiment

Run the next-round candidates with the same sample size and scoring rubric, then recompute the same cost components. If the top candidates remain close in `J_total`, add bootstrap confidence intervals or increase the response sample size before making a final prompt selection.
