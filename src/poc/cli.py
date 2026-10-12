"""Command line entry point for the conversion pipeline."""

import argparse
import logging
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser and its stage subcommands."""
    parser = argparse.ArgumentParser(prog="poc", description="Tender document conversion pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("extract", "enrich", "render", "verify", "report", "run"):
        subparser = subparsers.add_parser(command, help=f"{command.capitalize()} documents")
        if command in {"extract", "enrich", "verify"}:
            subparser.add_argument("--all", action="store_true", required=True, help="Extract all configured documents")
        if command == "enrich":
            subparser.add_argument("--provider", choices=("mock", "gemini", "groq"), help="Override LLM_PROVIDER")
        if command == "run":
            subparser.add_argument("--all", action="store_true", required=True, help="Run all configured documents")
            subparser.add_argument("--provider", choices=("mock", "gemini", "groq"), required=True, help="Provider name for interface compatibility; this demo reuses saved results only")
    convert = subparsers.add_parser("convert", help="Plan and convert one PDF using source element ids")
    convert.add_argument("input_pdf", type=Path)
    convert.add_argument("--out", type=Path, required=True)
    convert.add_argument("--provider", choices=("mock", "gemini", "groq"), required=True)
    probe = subparsers.add_parser("plan-check", help="Plan and validate one chunk without rendering")
    probe.add_argument("input_pdf", type=Path)
    probe.add_argument("--out", type=Path, required=True)
    probe.add_argument("--provider", choices=("mock", "gemini", "groq"), required=True)
    compare = subparsers.add_parser("compare", help="Compare LLM-planned and rule-only conversions")
    compare.add_argument("--all", action="store_true", required=True)
    subparsers.add_parser("llm-check", help="Check configured provider with one text and tiny-image request")
    return parser


def main() -> None:
    """Run the selected pipeline command."""
    args = build_parser().parse_args()
    if args.command == "llm-check":
        from poc.enrich import check_connection

        success, model = check_connection()
        print(f"LLM check: {'success' if success else 'failure'}; model={model}")
        if not success:
            raise SystemExit(1)
        return
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if args.command == "extract":
        from poc.extract import extract_all

        extract_all()
        return
    if args.command == "enrich":
        from poc.enrich import enrich_all

        results = enrich_all(provider_override=args.provider)
        for result in results:
            logging.info(
                "Enriched %s: %d headings (%d rule, %d LLM), %d/%d figures complete; %d provider calls, %d cache hits",
                result["doc_id"], result["headings"], result["classification"]["rule"],
                result["classification"]["llm"], result["figures_complete"], result["figures"],
                result["provider_calls"], result["cache_hits"],
            )
            if result["quota_hit"]:
                logging.error("Provider quota limit reached; remaining figures marked failed and no further real calls made")
        return
    if args.command == "render":
        from poc.render_docx import render_all

        render_all()
        return
    if args.command == "verify":
        from poc.verify import verify_all

        result = verify_all()
        for doc_id, metrics in result["documents"].items():
            logging.info(
                "Verified %s: %d defects, text recall %.4f, %d/%d mapping, %d/%d images, unplaced=%d",
                doc_id, len(metrics["defects"]), metrics["text"]["word_recall"] or 0.0,
                metrics["mapping"]["correct"], metrics["mapping"]["total"],
                metrics["images"]["docx_media_file_count"], metrics["images"]["source_display_image_count"],
                metrics["ledger"]["counts"]["unplaced"],
            )
        logging.info("Wrote data/output/metrics.json and data/output/verification.md")
        return
    if args.command == "report":
        from poc.report import write_accuracy_report, write_summary

        write_accuracy_report()
        write_summary()
        logging.info("Wrote docs/accuracy_report.md from data/output/metrics.json")
        return
    if args.command == "run":
        from poc.pipeline import run_all

        summary = run_all(provider_name=args.provider)
        for document in summary["documents"]:
            logging.info(
                "%s: placed=%d regenerated=%d unplaced=%d defects=%d",
                document["doc_id"], document["placed"], document["regenerated"],
                document["unplaced"], document["defects"],
            )
        doc_names = ", ".join(document["doc_id"] for document in summary["documents"])
        print(f"Run complete: {doc_names}; {summary['overall']['placed']} placed, "
              f"{summary['overall']['regenerated']} regenerated, {summary['overall']['unplaced']} unplaced, "
              f"{summary['overall']['defects']} defects")
        return
    if args.command == "convert":
        from poc.convert.runner import convert_pdf

        result = convert_pdf(args.input_pdf, args.out, provider_name=args.provider)
        print(f"Converted {Path(args.input_pdf).name}: {result['output_docx']}; calls={result['calls']}, retries={result['retries']}, fallbacks={len(result['fallbacks'])}, defects={len(result['verification']['defects'])}")
        return
    if args.command == "plan-check":
        from poc.convert.runner import plan_check_first_chunk

        result = plan_check_first_chunk(args.input_pdf, args.out, args.provider)
        print(f"Planner check succeeded: {result['element_count']} elements; calls={result['calls']}; cache_hits={result['cache_hits']}; plan={result['plan_path']}")
        return
    if args.command == "compare":
        from poc.convert.runner import compare_all

        result = compare_all()
        logging.info("Wrote docs/MODE_COMPARISON.md and data/output/mode_comparison.json for %d documents", len(result["documents"]))
        return
    logging.getLogger(__name__).info("%s is not implemented yet", args.command)


if __name__ == "__main__":
    main()
