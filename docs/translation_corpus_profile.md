# Canonical Translation Corpus Profile: VSL ↔ Vietnamese (10K)

## 1. Corpus Provenance & Overview
- **File Path**: `data/external/parallel_text/vie_vsl_10k.jsonl`
- **Format**: JSON Lines (`{"id": "PAR_10K_XXXXX", "vsl": "...", "vi": "..."}`)
- **Total Sentence Pairs**: **9,405**
- **Unique VSL Sequences**: **9,249** (98.34% unique)
- **Unique Vietnamese Sequences**: **9,388** (99.82% unique)
- **Exact Duplicate Pairs**: **0** (no verbatim duplicate pairs)
- **Duplicate VSL Sources**: **156** instances (140 unique VSL sentences mapping to 2+ distinct Vietnamese targets)
- **Duplicate Vietnamese Targets**: **17** instances (17 Vietnamese sentences with alternative VSL formulations)

---

## 2. Length Distributions

| Metric | Source VSL (Words) | Target Vietnamese (Words) | Source VSL (Chars) | Target Vietnamese (Chars) |
| :--- | :---: | :---: | :---: | :---: |
| **Minimum** | 1 | 2 | 1 | 3 |
| **Mean** | **7.53** | **8.88** | **29.41** | **34.05** |
| **Median** | **7.0** | **8.0** | **26.0** | **30.0** |
| **p90** | 12.0 | 14.0 | 50.0 | 57.0 |
| **p95** | 14.0 | 17.0 | 60.0 | 68.0 |
| **p99** | 18.0 | 21.0 | 78.0 | 89.0 |
| **Maximum** | 27 | 42 | 125 | 172 |

### Observation
- Average expansion ratio: $\frac{\text{Target Words}}{\text{Source Words}} = \frac{8.88}{7.53} \approx 1.18$.
- Target Vietnamese sentences are on average ~18% longer than VSL gloss sequences, as natural Vietnamese introduces grammatical particles, prepositions, copula verbs (`là`, `ở`, `của`, `và`), and modal markers that are omitted in VSL syntax.

---

## 3. Vocabulary Statistics

| Metric | Source VSL Vocabulary | Target Vietnamese Vocabulary |
| :--- | :---: | :---: |
| **Total Token Occurrences** | 70,820 | 83,516 |
| **Unique Tokens (Space-separated)** | **3,764** | **3,774** |
| **Singletons (Freq = 1)** | 1,028 (27.31%) | 954 (25.28%) |
| **Rare Tokens (Freq ≤ 5)** | 1,932 (51.33%) | 1,876 (49.71%) |

### Most Frequent Tokens
- **Source VSL**: `.`, `tôi`, `?`, `không`, `bạn`, `có`, `Tôi`, `một`, `cho`, `ở`, `thể`, `Bạn`, `được`, `đi`, `đó`, `nó`, `làm`, `anh`, `phải`, `đến`.
- **Target Vietnamese**: `.`, `tôi`, `?`, `không`, `bạn`, `có`, `Tôi`, `của`, `,`, `một`, `ở`, `cho`, `thể`, `được`, `Bạn`, `là`, `đó`, `đi`, `anh`, `và`.

---

## 4. One-to-Many and Many-to-One Mappings

### A. One VSL Mapping to Multiple Vietnamese Sentences (140 cases)
Examples of semantic ambiguity or alternative stylistic translations:
1. `VSL`: `"Tôi hiểu không ."`
   - `VI 1`: `"Tôi không hiểu ."`
   - `VI 2`: `"Tôi chưa hiểu rõ ."`
2. `VSL`: `"Bạn đi đâu ?"`
   - `VI 1`: `"Bạn đang đi đâu thế ?"`
   - `VI 2`: `"Bạn muốn đi đâu ?"`

### B. Multiple VSL Formulations Mapping to One Vietnamese Target (17 cases)
Examples where signers express the same meaning with different word orders:
1. `VI`: `"Tôi thích ăn kem ."`
   - `VSL 1`: `"Tôi kem ăn thích ."`
   - `VSL 2`: `"Tôi thích kem ăn ."`

---

## 5. Domain & Semantic Representation
- **Linguistic Nature of Source Field (`vsl`)**:
  The source field represents Vietnamese written according to Vietnamese Sign Language (VSL) syntax:
  - Topic-comment structures (`"Tôi sầu riêng không thích , hôi ."` $\to$ `"Tôi không thích sầu riêng vì nó hôi ."`)
  - Omission of copula verbs (`"Tôi học môn 4 ."` $\to$ `"Tôi học 4 môn ."`)
  - Sentence-final question particles (`"Biết bơi ai ?"` $\to$ `"Ai biết bơi ?"`)
  - Modal verbs following objects (`"Tôi xe mua muốn ."` $\to$ `"Tôi muốn mua xe ."`)
- **Compatibility**:
  Shares the exact syntactic structure as VSL-GH gloss annotations, requiring only case/separator normalization (`"TÔI MÈO THÍCH"` $\to$ `"tôi mèo thích"`).
