# Next-Round Prompt Candidates

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
