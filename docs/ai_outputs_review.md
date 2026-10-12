# AI Outputs Review — M3

Descriptions and transcriptions below are **AI-generated**. Token recall is **indicative** only: it measures the presence of selected keywords from `docs/answer_key.json`, not complete or faithful transcription. Figures are paired with key entries in stable extraction order. A key entry with no expected tokens is N/A and excluded from the aggregate denominator. Two scores are shown: strict case-insensitive substring matching, and normalized substring matching after lowercasing and removing hyphens and whitespace from both the transcription and keyword.

## Image descriptions and indicative token recall

### Waterfall

#### waterfall-p001-005

| Field | Value |
|---|---|
| Page | 1 |
| Kind | photo |
| AI-generated caption | A long-exposure photograph of Skógafoss waterfall cascading down lush green mossy cliffs into a misty pool surrounded by dark pebbled ground. |
| AI-generated transcribed text (reading order) | *(none)* |
| Answer-key token group | `cover_photo` |
| Strict token recall | N/A (0 expected tokens) — indicative |
| Normalized token recall | N/A (0 expected tokens) — indicative |
| Matched tokens | — |
| Missing tokens | — |

#### waterfall-p008-002

| Field | Value |
|---|---|
| Page | 8 |
| Kind | diagram |
| AI-generated caption | A circular diagram detailing the six phases of the software development life cycle. |
| AI-generated transcribed text (reading order) | 4<br>TESTING<br>5<br>DEPLOYMENT<br>3<br>DEVELOPMENT<br>SOFTWARE<br>DEVELOPMENT<br>LIFE CYCLE<br>6<br>MAINTENANCE<br>2<br>DESIGN<br>1<br>PLANNING |
| Answer-key token group | `sdlc_cycle` |
| Strict token recall | 7/7 (100.0%) — indicative |
| Normalized token recall | 7/7 (100.0%) — indicative |
| Matched tokens | SOFTWARE, DEVELOPMENT, PLANNING, DESIGN, TESTING, DEPLOYMENT, MAINTENANCE |
| Missing tokens | — |

#### waterfall-p008-007

| Field | Value |
|---|---|
| Page | 8 |
| Kind | diagram |
| AI-generated caption | A circular diagram outlining a five-step design and development process, highlighting an iterative cycle in step three. |
| AI-generated transcribed text (reading order) | Post-Deployment Review<br>Understand Environment of Use<br>5<br>1<br>MULTIPLE ITERATIONS<br>Summative Evaluation<br>4<br>2<br>Define User Needs<br>Concepts<br>3<br>Mockups<br>Hi-Fidelity Prototypes<br>Formative Evaluation<br>User Testing<br>Design & Development |
| Answer-key token group | `ux_cycle` |
| Strict token recall | 4/4 (100.0%) — indicative |
| Normalized token recall | 4/4 (100.0%) — indicative |
| Matched tokens | MULTIPLE ITERATIONS, Understand, Define, Evaluation |
| Missing tokens | — |

#### waterfall-p009-005

| Field | Value |
|---|---|
| Page | 9 |
| Kind | diagram |
| AI-generated caption | A circular diagram depicting the seven stages of the software testing life cycle, starting with requirement analysis and ending with test closure. |
| AI-generated transcribed text (reading order) | 1<br>Requirement Analysis<br>Understand requirements and testing needs<br>2<br>Test Planning<br>Define scope, strategy, resources and schedule<br>SOFTWARE TESTING LIFE CYCLE<br>3<br>Test Case Development<br>Design test cases and test data<br>4<br>Test Environment Setup<br>Prepare test environment and test data<br>5<br>Test Execution<br>Execute test cases and log results<br>6<br>Test Reporting & Analysis<br>Analyze results and report defects<br>7<br>Test Closure<br>Verify fixes and close testing |
| Answer-key token group | `testing_cycle` |
| Strict token recall | 4/4 (100.0%) — indicative |
| Normalized token recall | 4/4 (100.0%) — indicative |
| Matched tokens | SOFTWARE TESTING, Test Planning, Test Execution, Test Closure |
| Missing tokens | — |

#### waterfall-p010-001

| Field | Value |
|---|---|
| Page | 10 |
| Kind | diagram |
| AI-generated caption | A matrix diagram illustrating the phases of the software development lifecycle, detailing the associated activities and roles for each phase. |
| AI-generated transcribed text (reading order) | Phase<br>Planning<br>Analysis<br>Design<br>Implementation<br>Test<br>Deploy<br>Maintenance<br>Activities<br>Project Scope<br>User Requirements<br>System Architecture<br>Coding<br>System Testing<br>Deployment Plan<br>User Support<br>Resource Allocation<br>Technical Requirements<br>Design Specification<br>Unit Testing<br>User Acceptance Testing<br>Deploy to Production<br>Fix Issues and Bugs<br>Set Timelines<br>Functional Requirements<br>Integration Testing<br>Fix Bugs and Defects<br>User Training<br>Updates and New Features<br>Performance Monitoring<br>Roles<br>Product Owner<br>Business Analyst<br>System Architect<br>Front-end Developer<br>Solution Architect<br>DevOps<br>Users<br>Project Manager<br>Project Manager<br>UI/UX Designer<br>Back-end Developer<br>QA Engineer<br>Database Administrator<br>Support<br>CTO<br>Full stack Developer<br>Tester<br>SecOps<br>Developers<br>Database Administrator<br>Testers |
| Answer-key token group | `phase_role_chart` |
| Strict token recall | 7/7 (100.0%) — indicative |
| Normalized token recall | 7/7 (100.0%) — indicative |
| Matched tokens | Planning, Analysis, Design, Implementation, Test, Deploy, Maintenance |
| Missing tokens | — |

### Kanban

#### kanban-p004-016

| Field | Value |
|---|---|
| Page | 4 |
| Kind | diagram |
| AI-generated caption | A diagram illustrating the elements and layout of a Kanban board with labels for columns, swimlanes, cards, and workflow points. |
| AI-generated transcribed text (reading order) | Kanban Board<br>Commitment Point<br>Work In Progress (WIP) Limits<br>Delivery Point<br>Columns<br>To Do<br>In Progress<br>Done<br>Swimlanes<br>EXPEDITE<br>Cards |
| Answer-key token group | `board_diagram` |
| Strict token recall | 6/6 (100.0%) — indicative |
| Normalized token recall | 6/6 (100.0%) — indicative |
| Matched tokens | Kanban Board, Commitment Point, Delivery Point, Swimlanes, Cards, EXPEDITE |
| Missing tokens | — |

#### kanban-p005-008

| Field | Value |
|---|---|
| Page | 5 |
| Kind | diagram |
| AI-generated caption | A diagram comparing Kanban workflow performance without WIP limits versus with a WIP limit of five items, showing an increase in flow efficiency. |
| AI-generated transcribed text (reading order) | Without WIP Limits<br>Backlog<br>Ready<br>In Progress<br>Review<br>Done<br>Flow<br>Efficiency:<br>18%<br>5/5<br>With WIP Limit: 5 Items<br>Backlog<br>Ready<br>In Progress<br>Review<br>Done<br>Flow<br>Efficiency:<br>67%<br>67% |
| Answer-key token group | `wip_comparison` |
| Strict token recall | 4/4 (100.0%) — indicative |
| Normalized token recall | 4/4 (100.0%) — indicative |
| Matched tokens | Without WIP Limits, With WIP Limit, 18%, 67% |
| Missing tokens | — |

#### kanban-p007-008

| Field | Value |
|---|---|
| Page | 7 |
| Kind | diagram |
| AI-generated caption | A hand-drawn diagram illustrating Kanban practices across workflow stages from Backlog to Done. |
| AI-generated transcribed text (reading order) | VISUALIZE THE WORKFLOW<br>LIMIT WORK IN PROGRESS<br>MAKE POLICIES EXPLICIT<br>USE FEEDBACK LOOPS<br>BACKLOG<br>TO DO<br>WIP LIMIT<br>IN PROGRESS<br>REVIEW<br>DEPLOYMENT<br>DONE<br>BOTTLE-NECK<br>MANAGE FLOW<br>USE FEEDBACK LOOPS<br>IMPROVE COLLABORATIVELY |
| Answer-key token group | `flow_diagram` |
| Strict token recall | 3/4 (75.0%) — indicative |
| Normalized token recall | 4/4 (100.0%) — indicative |
| Strict matched tokens | MANAGE FLOW, VISUALIZE, LIMIT WORK IN PROGRESS |
| Strict missing tokens | BOTTLENECK |
| Normalized matched tokens | MANAGE FLOW, BOTTLENECK, VISUALIZE, LIMIT WORK IN PROGRESS |
| Normalized missing tokens | — |

## Classification table

Every first-level section was resolved by `config/classification.yaml`; all level-2 headings inherited their parent section type. The classification decision records use `method=rule` for these direct rule matches and inherited assignments. No heading required an LLM classification call.

| Document | Number | Heading title | Canonical type | Method | Status |
|---|---|---|---|---|---|
| Waterfall | 1 | Abstract | abstract | rule | complete |
| Waterfall | 2 | Scope | scope | rule | complete |
| Waterfall | 3 | Introduction | introduction | rule | complete |
| Waterfall | 3.1 | Background | introduction | rule (inherits 3) | complete |
| Waterfall | 3.2 | Purpose | introduction | rule (inherits 3) | complete |
| Waterfall | 3.3 | Scope | introduction | rule (inherits 3) | complete |
| Waterfall | 3.4 | Intended Audience | introduction | rule (inherits 3) | complete |
| Waterfall | 4 | Learning Objectives | learning_objectives | rule | complete |
| Waterfall | 5 | Waterfall Lifecycle | core_concept | rule | complete |
| Waterfall | 6 | Detailed Phase-by-Phase Explanation | process_detail | rule | complete |
| Waterfall | 6.1 | Requirements | process_detail | rule (inherits 6) | complete |
| Waterfall | 6.2 | Design | process_detail | rule (inherits 6) | complete |
| Waterfall | 6.3 | Development | process_detail | rule (inherits 6) | complete |
| Waterfall | 6.4 | Testing | process_detail | rule (inherits 6) | complete |
| Waterfall | 6.5 | Deployment | process_detail | rule (inherits 6) | complete |
| Waterfall | 6.6 | Maintenance | process_detail | rule (inherits 6) | complete |
| Waterfall | 7 | When to Use Waterfall | when_to_use | rule | complete |
| Waterfall | 7.1 | Decision Framework | when_to_use | rule (inherits 7) | complete |
| Waterfall | 8 | Best Practices | best_practices | rule | complete |
| Waterfall | 9 | Advantages of Waterfall | advantages | rule | complete |
| Waterfall | 10 | Limitations & Challenges | limitations | rule | complete |
| Kanban | 1 | Abstract | abstract | rule | complete |
| Kanban | 2 | Scope | scope | rule | complete |
| Kanban | 3 | Introduction | introduction | rule | complete |
| Kanban | 3.1 | Background | introduction | rule (inherits 3) | complete |
| Kanban | 3.2 | Purpose | introduction | rule (inherits 3) | complete |
| Kanban | 3.3 | Intended Audience | introduction | rule (inherits 3) | complete |
| Kanban | 4 | Learning Objectives | learning_objectives | rule | complete |
| Kanban | 5 | Kanban Methodology | core_concept | rule | complete |
| Kanban | 6 | Detailed Kanban Process Explanation | process_detail | rule | complete |
| Kanban | 6.1 | Visualizing Work | process_detail | rule (inherits 6) | complete |
| Kanban | 6.2 | Defining the Workflow | process_detail | rule (inherits 6) | complete |
| Kanban | 6.3 | Managing Work in Progress | process_detail | rule (inherits 6) | complete |
| Kanban | 6.4 | Managing Flow | process_detail | rule (inherits 6) | complete |
| Kanban | 6.5 | Continuous Improvement | process_detail | rule (inherits 6) | complete |
| Kanban | 7 | When to Use Kanban | when_to_use | rule | complete |
| Kanban | 8 | Best Practices | best_practices | rule | complete |
| Kanban | 9 | Advantages of Kanban | advantages | rule | complete |
| Kanban | 10 | Limitations & Challenges | limitations | rule | complete |

**Aggregate strict indicative image-token recall:** 35/36 (97.2%). **Aggregate normalized indicative image-token recall:** 36/36 (100.0%). These scores cover 7 figures with token expectations; the cover photograph has no key image tokens and is excluded. The metric only measures the presence of selected keywords, not complete transcription accuracy.
