# Stable Next-Round Prompt Candidates

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
