# Project Summary

## What we built

An offline-capable pipeline that extracts two PDFs into a structured intermediate representation, enriches figures from saved AI results, renders decision briefs in the configured Word template, and independently verifies the DOCX outputs.

## Accuracy in five lines

- Source text word recall: 100.00%; missing=0, excess=0.
- Tables: 8/8 shape and cell matches.
- Display images: 8/8; composites rebuilt=2/2.
- Section mapping: 20/20 (100.00%); image keywords indicative strict=35/36, normalised=36/36.
- Ledger: placed=121, regenerated=25, unplaced=0; defects=0.

## Top five challenges

1. Table extraction fragmented ruled cells; the line-based strategy and configured tolerances restored expected shapes.
2. Table-overlap suppression initially dropped adjacent bold text; per-line suppression plus word-conservation checks fixed it.
3. PDF image streams split logical figures; exact fragment bytes are retained and composites are rebuilt and checked.
4. Gemini could not be reached from the sandbox; the human completed enrichment and the saved results were reused offline.
5. An AI caption named unsupported place Skógafoss; the planned prompt rule will restrict descriptions to visible content and avoid names.

## What is not proven

Evidence covers two documents and our own template only. Image keyword presence is indicative, image transcription is not fully checked, and layout requires human visual comparison. The contents list is static and has no page numbers.

## Next steps

Have the architect review the generated DOCX and visual comparison, approve the accuracy evidence, and update the image prompt with the visible-content/no-names rule before any future real enrichment run.
