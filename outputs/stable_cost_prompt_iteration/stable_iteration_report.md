# Stable-Cost Prompt Iteration Report

## 1. Data overview

This stable-cost prompt iteration used 3500 scored responses from 7 prompt conditions in `round1/`.

| source_file        | prompt_id   | prompt_type                     | encoding  | original_rows | retained_rows | removed_missing_score_rows | normalization_method     | missing_columns | notes                                              |
| ------------------ | ----------- | ------------------------------- | --------- | ------------- | ------------- | -------------------------- | ------------------------ | --------------- | -------------------------------------------------- |
| qwen-prompt1-1.csv | Condition 1 | Baseline open prompt            | utf-8-sig | 500           | 500           | 0                          | scores already in [0, 1] |                 | response_text missing; retained as score-only file |
| qwen-prompt1-2.csv | Condition 2 | Role prompt                     | gb18030   | 500           | 500           | 0                          | scores already in [0, 1] |                 |                                                    |
| qwen-prompt1-3.csv | Condition 3 | Task-component prompt           | gb18030   | 500           | 500           | 0                          | scores already in [0, 1] |                 |                                                    |
| qwen-prompt1-4.csv | Condition 4 | Reasoning scaffold prompt       | gb18030   | 500           | 500           | 0                          | scores already in [0, 1] |                 |                                                    |
| qwen-prompt1-5.csv | Condition 5 | Knowledge-grounded prompt (RAG) | gb18030   | 500           | 500           | 0                          | scores already in [0, 1] |                 |                                                    |
| qwen-prompt1-6.csv | Condition 6 | Self-checking prompt            | gb18030   | 500           | 500           | 0                          | scores already in [0, 1] |                 |                                                    |
| qwen-prompt1-7.csv | Condition 7 | Demonstration prompt            | gb18030   | 500           | 500           | 0                          | scores already in [0, 1] |                 |                                                    |

## 2. New formula definition

`J_stable(P) = 0.30*C_disp + 0.25*C_norm + 0.20*C_peak + 0.15*C_region + 0.10*C_weak`.

Lower `J_stable` indicates that a prompt generates responses that are both closer to the ideal full-score explanation and less dispersed in the three-dimensional conceptual space.

## 3. Why v* is set to (1,1,1)

The revised target point is `v* = (1.00, 1.00, 1.00)` because the stable-cost workflow evaluates whether responses approach a full-score scientific explanation across D1, D2, and D3.

## 4. Why C_disp has the highest weight

`C_disp` receives the highest weight because this version prioritizes stable response distributions. However, low dispersion cannot override scientific quality; prompts with low dispersion but weak conceptual scores are still penalized by `C_norm`, `C_peak`, `C_region`, and `C_weak`.

## 5. Prompt ranking by J_stable

| rank | prompt_id   | prompt_type                     | N   | mean_D1 | mean_D2 | mean_D3 | P_omega | C_disp | C_norm | C_peak | C_region | J_stable | main_problem                                              | second_problem                                              |
| ---- | ----------- | ------------------------------- | --- | ------- | ------- | ------- | ------- | ------ | ------ | ------ | -------- | -------- | --------------------------------------------------------- | ----------------------------------------------------------- |
| 1    | Condition 3 | Task-component prompt           | 500 | 0.8516  | 0.9980  | 0.9820  | 0.7220  | 0.1088 | 0.0936 | 0.0000 | 0.2780   | 0.0977   | C_region: Too few responses enter the high-quality region | C_disp: Responses are too dispersed                         |
| 2    | Condition 7 | Demonstration prompt            | 500 | 0.7672  | 1.0000  | 0.9848  | 0.6500  | 0.0903 | 0.1395 | 0.1155 | 0.3500   | 0.1387   | C_region: Too few responses enter the high-quality region | C_norm: Responses are not close enough to full-score target |
| 3    | Condition 4 | Reasoning scaffold prompt       | 500 | 0.9132  | 0.9996  | 0.8156  | 0.5220  | 0.1438 | 0.1402 | 0.0000 | 0.4780   | 0.1499   | C_region: Too few responses enter the high-quality region | C_disp: Responses are too dispersed                         |
| 4    | Condition 2 | Role prompt                     | 500 | 0.8136  | 0.9868  | 0.7944  | 0.6420  | 0.1580 | 0.1909 | 0.1155 | 0.3580   | 0.1721   | C_region: Too few responses enter the high-quality region | C_norm: Responses are not close enough to full-score target |
| 5    | Condition 1 | Baseline open prompt            | 500 | 0.7284  | 0.9944  | 0.7080  | 0.2620  | 0.1675 | 0.2585 | 0.2582 | 0.7380   | 0.2827   | C_region: Too few responses enter the high-quality region | C_norm: Responses are not close enough to full-score target |
| 6    | Condition 5 | Knowledge-grounded prompt (RAG) | 500 | 0.4784  | 1.0000  | 0.9876  | 0.1800  | 0.0991 | 0.3031 | 0.3464 | 0.8200   | 0.3085   | C_region: Too few responses enter the high-quality region | C_peak: Most frequent response type is not ideal            |
| 7    | Condition 6 | Self-checking prompt            | 500 | 0.3928  | 0.9604  | 0.9992  | 0.0200  | 0.1091 | 0.3570 | 0.3464 | 0.9800   | 0.3518   | C_region: Too few responses enter the high-quality region | C_norm: Responses are not close enough to full-score target |

## 6. Diagnosis of the best prompts

The best prompt is **Condition 3 (Task-component prompt)**, with `J_stable = 0.0977`. Its main remaining problem is **C_region: Too few responses enter the high-quality region**, and its second remaining problem is **C_disp: Responses are too dispersed**.

The recalculated stable cost confirms the expected two-base pattern: the top prompts include the demonstration prompt and the task-component prompt.

本研究依据稳定性优先的 cost function 选择优化提示词，而不是仅依据平均分。较低的 J_stable 表明该提示词既能使回答更接近三个维度均为满分的理想科学解释，也能使回答在三维概念空间中的分布更加集中稳定。

## 7. Next-round prompt generation logic

Second-round prompts were generated only after recalculating first-round stable costs. The selected design uses the top stable-cost bases and tests replication, component coherence, demonstration plus full-score target, component-example hybridization, and explicit stability optimization.

## 8. Next-round prompt candidates

### Stable_R2_1_task_component_replication

- source_prompt_id: Condition 3
- source_prompt_type: Task-component prompt
- target_cost_component: replication baseline
- diagnosed_problem: Condition 3 is the lowest J_stable prompt and needs a direct task-component baseline in round 2
- revision_strategy: replicate the best task-component base to confirm first-round stability under the new formula
- expected_effect: provides a direct benchmark for full-score target and normative-region entry
- possible_side_effect: does not test a new repair operation

```text
请从能量角度解释石块从高空落下这一现象。回答需要明确包含三个任务组件：第一，说明重力势能和动能如何变化；第二，说明机械能在什么条件下守恒；第三，使用准确的科学术语进行表达。请将三个组件组织成一段连贯解释。
```

### Stable_R2_2_demonstration_replication

- source_prompt_id: Condition 7
- source_prompt_type: Demonstration prompt
- target_cost_component: replication baseline
- diagnosed_problem: Condition 7 has the strongest demonstration-guided stability and needs a direct demonstration baseline in round 2
- revision_strategy: replicate the best demonstration base to confirm its stable response distribution
- expected_effect: provides a direct benchmark for demonstration-guided stability
- possible_side_effect: does not test a new repair operation

```text
请仿照这样的高质量解释方式回答：先指出石块在高处具有重力势能；下落时重力势能减少并转化为动能；若忽略空气阻力，机械能近似守恒；若考虑空气阻力，部分机械能会转化为热能、声能等。现在请用类似的方式，从能量角度解释石块从高空落下这一现象。
```

### Stable_R2_3_component_coherence

- source_prompt_id: Condition 3
- source_prompt_type: Task-component prompt
- target_cost_component: C_disp + C_region
- diagnosed_problem: C_region: Too few responses enter the high-quality region; C_disp: Responses are too dispersed
- revision_strategy: combine minimum components with a stable explanation order
- expected_effect: should reduce dispersion while increasing normative-region entry
- possible_side_effect: strong structure may increase over-template responses

```text
请从能量角度解释石块从高空落下这一现象。回答至少包含：重力势能和动能如何变化、机械能在什么条件下守恒、存在空气阻力时能量如何转化，以及准确科学术语。请按“能量转化、守恒条件、空气阻力、术语总结”的顺序写成一段连贯解释。
```

### Stable_R2_4_demo_full_score_target

- source_prompt_id: Condition 7
- source_prompt_type: Demonstration prompt
- target_cost_component: C_norm + C_peak
- diagnosed_problem: C_norm: Responses are not close enough to full-score target; C_peak is also checked because the target point is now (1,1,1)
- revision_strategy: keep demonstration stability while making the full-score pattern explicit
- expected_effect: should move the common response pattern closer to (1,1,1)
- possible_side_effect: may reduce naturalness if the target components become too rigid

```text
请仿照高质量科学解释的方式，从能量角度解释石块从高空落下。一个满分解释应同时说明：重力势能向动能转化、无空气阻力时机械能守恒的条件、有空气阻力时部分机械能转化为热能或声能，以及重力势能、动能、机械能守恒等术语的准确使用。请组织成自然连贯的一段话。
```

### Stable_R2_5_component_example_hybrid

- source_prompt_id: Condition 3
- source_prompt_type: Task-component prompt
- target_cost_component: C_disp + C_norm + C_peak
- diagnosed_problem: C_region: Too few responses enter the high-quality region; C_disp: Responses are too dispersed; full-score proximity is targeted by v*=(1,1,1)
- revision_strategy: combine full-score components with example-guided stability
- expected_effect: should retain component completeness while improving response stability
- possible_side_effect: hybrid prompt is longer and may create formulaic answers

```text
请根据下面的解释框架回答：先说明石块在高处具有重力势能；再说明下落时重力势能减少、动能增加；接着说明在忽略空气阻力时机械能近似守恒；然后说明真实情况下空气阻力会使部分机械能转化为热能、声能等；最后用准确术语总结。请用这个框架解释石块从高空落下，但不要只罗列要点，要写成连贯说明。
```

### Stable_R2_6_stability_optimized

- source_prompt_id: Condition 7
- source_prompt_type: Demonstration prompt
- target_cost_component: C_disp
- diagnosed_problem: C_region: Too few responses enter the high-quality region; stability is explicitly stress-tested because C_disp has the highest formula weight
- revision_strategy: explicitly test a stable explanation structure
- expected_effect: should test whether strong structure reduces conceptual dispersion
- possible_side_effect: very low dispersion may indicate homogenized or over-template responses

```text
请使用稳定的解释结构：先说明能量转化，再说明机械能守恒的条件，然后解释存在空气阻力时会发生什么变化，最后使用准确的科学术语进行总结。请保持解释连贯，并避免遗漏上述部分。
```

## 9. Risks, especially over-template responses

Because `C_disp` has the highest weight, prompts that impose a strong structure may reduce dispersion while also making responses overly homogeneous. The second round should inspect response text, not only scores, especially for the stability-optimized condition.

## 10. Recommended next experiment

Run the six stable-cost second-round prompts with the same response count and scoring rubric. Recompute `J_stable`; then compare whether the hybrid prompts improve both full-score proximity and dispersion without producing over-template responses.
