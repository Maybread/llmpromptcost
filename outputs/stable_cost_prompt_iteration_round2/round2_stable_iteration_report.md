# Round 2 Stable-Cost Component Analysis

## Data overview

This analysis used 1500 scored responses from 3 prompt conditions in `round2/`.

| source_file             | prompt_id | prompt_type                          | encoding  | original_rows | retained_rows | removed_missing_score_rows | normalization_method     | missing_columns | notes                                                                                                |
| ----------------------- | --------- | ------------------------------------ | --------- | ------------- | ------------- | -------------------------- | ------------------------ | --------------- | ---------------------------------------------------------------------------------------------------- |
| qwen-prompt1-3.csv      | R1-C3     | Task-component baseline from round 1 | gb18030   | 500           | 500           | 0                          | scores already in [0, 1] |                 |                                                                                                      |
| qwen-prompt1-7.csv      | R1-C7     | Demonstration baseline from round 1  | gb18030   | 500           | 500           | 0                          | scores already in [0, 1] |                 |                                                                                                      |
| PHYSICS-R2-C3-score.csv | R2-P3*P7  | Round 2 optimized prompt             | utf-8-sig | 500           | 500           | 0                          | scores already in [0, 1] |                 | response_text missing; retained as score-only round2 file; mapped Score->D1, score2->D2, Score_3->D3 |

## Formula

`J_stable(P) = 0.20*C_disp + 0.20*C_norm + 0.20*C_peak + 0.20*C_region + 0.20*C_weak`.

`C_disp` uses the root-mean-square normalized distance from each response to its prompt-level mean point.

## Prompt ranking

| rank | prompt_id | prompt_type                          | N   | mean_D1 | mean_D2 | mean_D3 | P_omega | C_disp | C_norm | C_peak | C_region | C_weak | J_stable | main_problem                                              | second_problem                                              |
| ---- | --------- | ------------------------------------ | --- | ------- | ------- | ------- | ------- | ------ | ------ | ------ | -------- | ------ | -------- | --------------------------------------------------------- | ----------------------------------------------------------- |
| 1    | R2-P3*P7  | Round 2 optimized prompt             | 500 | 0.9996  | 1.0000  | 0.8888  | 0.8920  | 0.0787 | 0.0644 | 0.0000 | 0.1080   | 0.0000 | 0.0502   | C_region: Too few responses enter the high-quality region | C_disp: Responses are too dispersed                         |
| 2    | R1-C3     | Task-component baseline from round 1 | 500 | 0.8516  | 0.9980  | 0.9820  | 0.7220  | 0.1088 | 0.0936 | 0.0000 | 0.2780   | 0.0000 | 0.0961   | C_region: Too few responses enter the high-quality region | C_disp: Responses are too dispersed                         |
| 3    | R1-C7     | Demonstration baseline from round 1  | 500 | 0.7672  | 1.0000  | 0.9848  | 0.6500  | 0.0903 | 0.1395 | 0.1155 | 0.3500   | 0.0328 | 0.1456   | C_region: Too few responses enter the high-quality region | C_norm: Responses are not close enough to full-score target |

## Weighted component contributions

| prompt_id | weighted_C_disp | weighted_C_norm | weighted_C_peak | weighted_C_region | weighted_C_weak | J_stable |
| --------- | --------------- | --------------- | --------------- | ----------------- | --------------- | -------- |
| R2-P3*P7  | 0.0157          | 0.0129          | 0.0000          | 0.0216            | 0.0000          | 0.0502   |
| R1-C3     | 0.0218          | 0.0187          | 0.0000          | 0.0556            | 0.0000          | 0.0961   |
| R1-C7     | 0.0181          | 0.0279          | 0.0231          | 0.0700            | 0.0066          | 0.1456   |

## Interpretation

The lowest-cost prompt in this round is **R2-P3*P7 (Round 2 optimized prompt)**, with `J_stable = 0.0502`.

The new score-only file `PHYSICS-R2-C3-score.csv` was mapped as `Score -> D1`, `score2 -> D2`, and `Score_3 -> D3`. The original `qwen-prompt1-3.csv` and `qwen-prompt1-7.csv` files were used directly and labeled as `R1-C3` and `R1-C7`.

Because this analysis compares only scored dimensions, inspect response text separately before concluding that a very low dispersion result is substantively better. Low dispersion can also reflect overly templated answers.
