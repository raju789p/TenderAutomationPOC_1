# Accuracy Report

## Goal and method

Measure whether two source PDFs are preserved in our configured Word template. The deterministic workflow is extract → intermediate representation (IR) → target template → render → independent verification. AI-generated image descriptions are saved enrichment metadata; the document conversion itself uses extracted source content.

## Results

| Document | Text recall | Tables | Headings | Images | Composites | Mapping accuracy | Image keywords strict | Image keywords normalised | Placed / regenerated / unplaced | Defects |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| waterfall | 100.00% | 5/5 | 21/21 | 5/5 | 1/1 | 10/10 (100.00%) | 22/22 | 22/22 | 58 / 16 / 0 | 0 |
| kanban | 100.00% | 3/3 | 18/18 | 3/3 | 1/1 | 10/10 (100.00%) | 13/14 | 14/14 | 63 / 9 / 0 | 0 |
| Overall | 100.00% | 8/8 | 39/39 | 8/8 | 2/2 | 20/20 (100.00%) | 35/36 | 36/36 | 121 / 25 / 0 | 0 |

Heading coverage: 39/39 (100.00%); contents topics represented as headings: 20/20.
Composite rebuilds matched: 2/2. Image keyword recall is **indicative; measures keyword presence only**: strict 35/36 (97.22%); normalised 36/36 (100.00%).

## What the verifier checks

The independent DOCX verifier checks source-word recall and excess words, table shape and whitespace-normalised cell equality, heading titles and levels, display-image media hashes and counts, composite rebuilds from exact parts, placement order, contents topics, section mapping, the disposition ledger, and private-use Unicode characters. The offline corruption suite verifies detection of: delete a table row; swap one image; change one paragraph word; delete one paragraph; change a heading title; move a section out of order; insert a private-use character.

## Limits of this evidence

- Only two source documents were measured.
- The target is our own configured template, not an external organisation's approved template.
- Image keyword recall is indicative only: it measures selected keyword presence, not full transcription accuracy.
- Text inside images cannot be verified automatically against a complete human transcription.
- Layout still needs human visual review against the source PDFs.
- The contents list is static and has no page numbers.
- Results come from the deterministic pipeline, not from an LLM-generated conversion.

## Known issues

One AI-generated caption named **Skógafoss**, a place name not supported by the source image. This is a caption hallucination risk. The planned prompt rule is: **describe only what is visible; no place, person or brand names**. Existing saved AI outputs are preserved; no new model request was made for this report.

Image keyword metrics do not evaluate that caption claim; human review remains necessary.
