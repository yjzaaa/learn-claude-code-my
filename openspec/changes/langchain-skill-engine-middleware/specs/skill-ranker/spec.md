## ADDED Requirements

### Requirement: BM25 + Embedding hybrid ranking
The SkillRanker SHALL implement two-stage hybrid ranking.

#### Scenario: BM25 pre-filtering
- **GIVEN** 20 skills and a query
- **WHEN** ranking is performed with top_k=5
- **THEN** BM25 stage returns top 15 candidates (top_k * 3)

#### Scenario: Embedding re-ranking
- **GIVEN** BM25 returned 15 candidates
- **WHEN** embedding stage executes
- **THEN** it computes similarities and returns top 5

#### Scenario: BM25-only mode
- **GIVEN** embedding is disabled or no API key
- **WHEN** ranking is performed
- **THEN** only BM25 is used, returning top_k results directly

### Requirement: Embedding caching
The SkillRanker SHALL cache embeddings locally.

#### Scenario: Cache hit
- **GIVEN** skill was previously embedded
- **WHEN** ranking is performed again
- **THEN** cached embedding is reused without API call

#### Scenario: Cache miss
- **GIVEN** skill has no cached embedding
- **WHEN** ranking is performed
- **THEN** embedding is computed via API and stored in cache

#### Scenario: Cache persistence
- **GIVEN** cache contains embeddings
- **WHEN** application restarts
- **THEN** cache is loaded from disk pickle file

#### Scenario: Cache invalidation
- **GIVEN** skill content was modified
- **WHEN** ranking is performed
- **THEN** mtime change is detected and embedding is recomputed

### Requirement: Embedding text building
The SkillRanker SHALL build consistent embedding text.

#### Scenario: Standard skill text
- **GIVEN** skill with name, description, and body
- **WHEN** embedding text is built
- **THEN** format is "{name}\n{description}\n\n{body[:8000]}"

#### Scenario: Truncation
- **GIVEN** skill body exceeds 12000 characters
- **WHEN** embedding text is built
- **THEN** body is truncated to 12000 chars to fit token limit

### Requirement: Pre-filter threshold
The SkillRanker SHALL skip embedding for small skill sets.

#### Scenario: Below threshold
- **GIVEN** 8 skills (below PREFILTER_THRESHOLD=10)
- **WHEN** ranking is performed
- **THEN** embedding is computed for all skills without BM25 pre-filter

#### Scenario: Above threshold
- **GIVEN** 15 skills (above threshold)
- **WHEN** ranking is performed
- **THEN** BM25 pre-filter reduces candidates to 30 before embedding

### Requirement: Cosine similarity scoring
The SkillRanker SHALL use cosine similarity for embedding comparison.

#### Scenario: Perfect match
- **GIVEN** query and candidate embeddings are identical
- **WHEN** similarity is computed
- **THEN** score is 1.0

#### Scenario: Orthogonal vectors
- **GIVEN** query and candidate are completely unrelated
- **WHEN** similarity is computed
- **THEN** score approaches 0.0

#### Scenario: Combined score
- **GIVEN** BM25 score is 0.8 and embedding score is 0.9
- **WHEN** final ranking is determined
- **THEN** embedding score is used (secondary stage replaces primary)
