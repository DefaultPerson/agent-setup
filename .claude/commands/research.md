---
description: Conduct competitor analysis or technical research with structured output to research/.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding.

## Outline

### Phase 0: Setup

1. **Parse topic** from `$ARGUMENTS`
   - If empty, ask user what to research

2. **Auto-detect research mode** based on topic keywords:
   - **Competitor Analysis**: "alternatives", "vs", "competitors", "pricing", "compare", product/company names
   - **Technical Research**: "API", "how to", "best practices", "parsing", "library", "framework", "implementation", "github"
   - If unclear, proceed with general research approach

3. **Generate output path**:
   - Slugify topic: lowercase, replace spaces with `-`, remove special chars
   - Path: `{REPO_ROOT}/research/{topic-slug}.md`
   - Create directory if not exists: `mkdir -p research`

4. **Initialize research document** with metadata (atomic write):
   ```markdown
   # Research: {Topic}

   **Date**: {YYYY-MM-DD}
   **Mode**: {Detected Mode}
   **Status**: In Progress
   ```

5. **Generate subtopics** (query decomposition):
   - Decompose main topic into 3-5 focused subtopics
   - Adapt subtopics based on detected mode:

   **For Competitor Analysis**:
   - What is {topic}? (market category, core value prop)
   - Who are the main players? (direct competitors)
   - How do they compare? (features, pricing, positioning)
   - What are the problems? (complaints, limitations)
   - What do users recommend? (community preferences)

   **For Technical Research**:
   - What is {topic}? (definition, core concepts)
   - How does it work? (mechanics, implementation)
   - What are the alternatives? (other approaches)
   - What are the problems? (limitations, gotchas)
   - What are best practices? (recommendations, patterns)

   Show the research plan to user before starting deep research.

### Phase 1: Scope Clarification (if needed)

Only ask clarifying questions if topic is genuinely ambiguous. **Max 3 questions.**

Present questions one at a time with recommendation:

**Recommended:** Option X - {reasoning}

| Option | Description |
|--------|-------------|
| A | ... |
| B | ... |

Possible questions (only if truly unclear):
1. **Scope**: Which aspects are most important? (features, pricing, implementation, all)
2. **Depth**: Quick overview or deep dive?
3. **Targets**: Any specific products/libraries to include or exclude?

Skip clarification if topic is clear enough to proceed.

### Phase 2: Deep Research Execution

**Core principle: Multi-pass search with parallel exploration and source triangulation.**

#### Step 1: Parallel Subagent Research (MANDATORY for complex topics)

**CRITICAL**: You MUST use the Agent tool to spawn parallel agents. This is the ONLY way to achieve true parallelism and depth.

For each major subtopic from Phase 0, launch a dedicated agent with `run_in_background: true`:

```
Launch 2-3 agents in parallel (run_in_background: true):

Agent(
  subagent_type="general-purpose",
  description="Research {topic} definition",
  prompt="Research subtopic: What is {topic}? Find: definition, core concepts, how it works. Use WebSearch and WebFetch. Return structured findings with sources. Be thorough.",
  run_in_background=true
)

Agent(
  subagent_type="general-purpose",
  description="Research {topic} alternatives",
  prompt="Research subtopic: Alternatives to {topic}. Search for competitors, compare features/pricing. Use site:github.com for open-source options. Return structured findings with sources.",
  run_in_background=true
)

Agent(
  subagent_type="general-purpose",
  description="Research {topic} problems",
  prompt="Research subtopic: Problems with {topic}. Search HN (site:news.ycombinator.com), Reddit (site:reddit.com) for real user complaints and limitations. Return structured findings with sources.",
  run_in_background=true
)
```

**Rules for parallel research**:
- Launch 2-3 agents with `run_in_background: true` for parallel execution
- Each agent gets ONE focused subtopic
- Agents should use WebSearch, WebFetch, Context7
- Wait for all agents to complete before moving to Step 2
- For simple topics: skip parallel agents, do sequential search

#### Step 2: Multi-Pass Search Strategy

After parallel research, fill gaps with targeted passes:

**Pass 1 — Broad Discovery** (if not done by agents):
- General queries about the topic
- Overview articles, official docs

**Pass 2 — Expert Sources**:
- `site:news.ycombinator.com {topic}` — developer opinions, real experiences
- `site:reddit.com {topic}` — community insights, discussions
- `site:arxiv.org {topic}` — academic research (if technical)
- `site:github.com {topic} stars:>100` — proven solutions, popular repos
- Context7 for library/framework documentation

**Pass 3 — Gap Analysis & Targeted Search**:
After each pass, evaluate internally:
- What's confirmed? What's still missing?
- What claims need verification from another source?
- Generate targeted queries for gaps

**Pass 4 — Counter-Arguments** (ALWAYS do this):
- `{topic} problems`
- `{topic} criticism`
- `{topic} vs {alternative}`
- `why not use {topic}`
- `{topic} downsides`

**Pass 5 — Source Triangulation**:
For key facts (pricing, performance, features):
- Verify from 2-3 independent sources
- Note conflicting information explicitly

#### Tools

- **WebSearch**: Primary search tool for discovery
- **WebFetch**: Deep reading of specific pages (docs, pricing, features)
- **Context7**: Library/framework documentation lookup
- **Agent**: Parallel subagent research (subagent_type: general-purpose, run_in_background: true)

#### Atomic Writes

After each significant block of findings, write to the research document:
- After parallel agents complete
- After each pass that yields new information
- After gap analysis reveals new findings

#### Stopping Criteria

- All subtopics from Phase 0 covered
- Key claims verified from multiple sources
- Counter-arguments documented
- New searches don't yield new information
- User says "enough"

### Phase 3: Synthesis & Documentation

#### Confidence Ratings

Use emoji indicators for claim confidence throughout the document:
- 🟢 **High**: 3+ sources, official docs, recent data
- 🟡 **Medium**: 1-2 sources, reasonably recent
- 🔴 **Low/Unverified**: Single source, outdated, or conflicting info

Apply ratings to key claims:
```markdown
- 🟢 Pricing starts at $10/month (official website, 2 reviews)
- 🟡 Supports up to 10k req/sec (one benchmark, 2024)
- 🔴 Planning to add feature X (single blog mention, unconfirmed)
```

Structure findings based on detected mode:

#### For Competitor Analysis

```markdown
## Executive Summary
{2-3 paragraphs: key findings, market landscape, recommendation}

## Market Overview
{Brief description of the market/category}

## Competitors

### {Competitor 1}
- **Overview**: {what it is, who it's for}
- **Key Features**: {bullet list}
- **Pricing**: {tiers, free tier, enterprise options}
- **Strengths**: {what they do well}
- **Weaknesses**: {gaps, issues, limitations}
- **User Sentiment**: {reviews summary if found}

### {Competitor 2}
...

## Feature Comparison

| Feature | {Comp 1} | {Comp 2} | {Comp 3} |
|---------|----------|----------|----------|
| ... | ... | ... | ... |

## Pricing Comparison

| Tier | {Comp 1} | {Comp 2} | {Comp 3} |
|------|----------|----------|----------|
| Free | ... | ... | ... |
| Pro | ... | ... | ... |

## Recommendations
- **Primary**: {what to choose and why}
- **Alternatives**: {when to consider others}
- **Open Questions**: {what needs further investigation}
```

#### For Technical Research

```markdown
## Executive Summary
{2-3 paragraphs: problem, solution approach, recommendation}

## Technology Overview
{What the technology/approach is about}

## Best Practices
- **{Practice 1}**: {description + rationale}
- **{Practice 2}**: {description + rationale}

## Implementation Patterns

### Pattern: {Name}
```{language}
{code example if applicable}
```
**When to use**: {context}
**Trade-offs**: {pros/cons}

## Alternatives Comparison

| Criterion | {Option 1} | {Option 2} | {Option 3} |
|-----------|------------|------------|------------|
| Performance | ... | ... | ... |
| Complexity | ... | ... | ... |
| Community | ... | ... | ... |

## Security Considerations
- {Security concern 1}
- {Security concern 2}

## Recommendations
- **Primary**: {recommended approach}
- **Alternatives**: {when to consider others}
- **Open Questions**: {what needs team decision}
```

### Phase 4: Finalize & Report

1. Update document status to "Final"

2. Add **Disputed/Unverified Claims** section (if any):
   ```markdown
   ## Disputed/Unverified Claims
   - {Claim 1}: {why uncertain — conflicting sources, single mention, etc.}
   - {Claim 2}: {needs verification — only found in one place}
   ```

3. Add **Research Metadata**:
   ```markdown
   ## Research Metadata
   - **Sources consulted**: {N}
   - **Search passes**: {N}
   - **Subtopics covered**: {list}
   - **Parallel agents used**: Yes/No
   - **Research depth**: Deep / Standard
   ```

4. Compile **Sources** section with annotations:
   ```markdown
   ## Sources
   1. [{Title}]({URL}) - {brief annotation: why valuable}
   2. ...
   ```

5. Report to user:
   - Path to research document
   - Brief summary of key findings (3-5 bullet points)
   - Highlight any disputed/unverified claims
   - Suggested next steps if applicable

## Rules

- **Absolute paths** only
- **Atomic writes** after each significant finding block
- **No hardcoded query templates** — generate dynamically
- **No artificial search limits** — research until topic is covered
- **Sources at end**, not inline
- Match **user's language** in output
- Single quotes escaping: `'I'\''m Groot'`

## Error Handling

- If no relevant results: note the gap, suggest query refinement
- If conflicting information: document both perspectives, recommend verification approach
- If search fails: retry once, then document limitation

## Examples

```
/research telegram aggregator alternatives
/research CoinGecko API alternatives
/research NATS vs Kafka for real-time events
/research telegram message parsing best practices
/research python async web scraping
/research github telegram bot python
```
