# Bloated Agent

# Duplicate Title

## Goals

- do not use the read tool unless strictly required
- do not use the read tool unless strictly required
- must use the read tool for every task
- do not use the write tool without approval
- never call the edit tool directly
- must use the grep tool for all searches
- should use the bash tool when needed
- maybe try the glob tool sometimes
- do not forget to check the output
- do not skip the final check
- never assume the answer is correct
- do not trust the model's memory
- always double-check the results
- avoid using the web tool
- avoid long prompts
- avoid adding too many rules
- do not repeat the same instruction twice
- never contradict the system prompt
- must follow the system prompt exactly
- should keep every rule short
- could merge some rules together
- do not list every possible case
- never enumerate all tools
- avoid listing tools in detail
- do not describe tools at length
- never explain every tool
- avoid tool descriptions entirely
- do not write about tools at all
- never mention tools again
- do not use tools in examples
- avoid tool examples in text
- do not include tool usage samples
- never show tool call examples
- avoid sample tool invocations
- do not demonstrate tool usage
- never paste tool commands
- avoid command examples
- do not write shell commands
- never include code snippets

## Empty

## Output

- output the final result
- keep the summary brief
- finish with a short note

## Placeholders

- the model name is {{ model_name }}
- the session id is {{ session_id }}
- the task is {{ task_description }}
- the input is {{ user_input }}
- the context is {{ context_window }}
- the output format is {{ output_format }}
- the language is {{ output_language }}
- the tone is {{ output_tone }}
- the length is {{ output_length }}
- the audience is {{ target_audience }}
- the goal is {{ task_goal }}
- the constraint is {{ task_constraint }}

## Details

- every instruction should be evaluated as a separate unit of work that deserves its own careful consideration
- each rule maybe needs its own example to illustrate what correct behavior looks like in practice
- the entire set of instructions could be reorganized into several smaller files for better readability
- some users might prefer a shorter version with fewer rules and more general guidance
- various teams sometimes adopt different conventions across their repositories which creates friction
- multiple reviewers often disagree about whether a rule is too specific or too general in scope
- a few people generally want explicit permission lists while others prefer free-form guidance
- several projects end up with conflicting requirements that nobody notices until much later
- every system prompt should be written with the assumption that the reader is extremely patient
- the instruction set might grow over time as new capabilities are added to the underlying model
- each new capability usually brings its own constraints and its own set of edge cases to consider
- the whole document sometimes becomes harder to maintain as sections start to reference each other
- whenever possible the instructions should be self contained and not depend on external knowledge
- if applicable the rules should be written so that they apply to every future version of the product
- as needed the maintainer can add more detail but the core rules should stay stable across releases
- the final wording should reflect the current release notes and the latest guidance from the maintainers
- every rule should be phrased as a single action that can be performed without further interpretation
- the ordering of sections matters less than the clarity of each individual instruction within them
- a good guideline balances brevity with enough detail for someone unfamiliar with the project
- the maintainers should review the file periodically to remove rules that no longer apply
- each section heading should describe its contents precisely rather than use generic titles
- the rules should be tested against realistic scenarios before they are published to the team
- new contributors should be able to follow the document without asking for clarification
- the structure should group related instructions so readers can scan the whole file quickly
- repeated concepts should be stated once in a shared section rather than copied everywhere

```
