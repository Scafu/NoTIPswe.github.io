import subprocess
import os
import sys
import logging
import argparse

import docs_lib


def setup_logging():
    """Configures logging."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def compile_document(doc: docs_lib.Document, output_dir: str):
    """Compiles a single, validated Document object."""

    source_dir = os.path.dirname(doc.source) or "."
    changelog_path_relative = os.path.relpath(doc.changelog_path, start=source_dir)

    complete_output_path = os.path.join(output_dir, doc.output)

    logging.info(f"Compiling '{doc.title}': {doc.source} -> {complete_output_path}")

    command = [
        "typst",
        "compile",
        doc.source,
        complete_output_path,
        "--input",
        f"changelog_path={changelog_path_relative}",
        "--input",
        f"doc_title={doc.title}",
        "--root",
        ".",
    ]
    logging.debug(f"Executing: {' '.join(command)}")

    try:
        subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", check=True
        )
        logging.info(f"SUCCESS: '{doc.title}' compiled.")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(
            f"FAILURE: Compiling '{doc.title}' failed.\n--- START ---\n{e.stderr.strip()}\n--- END ---"
        )
        return False
    except FileNotFoundError:
        logging.critical("Typst command not found. Is it installed and in your PATH?")
        sys.exit(1)


def main():
    """Main function to orchestrate the build process."""
    setup_logging()

    parser = argparse.ArgumentParser(description="Build Typst documents.")
    parser.add_argument(
        "--outdir",
        default="docs-output",
        help="Output directory for compiled documents.",
    )
    args = parser.parse_args()
    output_dir = args.outdir

    logging.debug(f"Ensuring output directory '{output_dir}' exists...")
    os.makedirs(output_dir, exist_ok=True)

    document_model = docs_lib.load_documents_model()

    if not document_model:
        # This case is handled by the library (warning is logged), but we exit cleanly.
        return

    logging.info(
        f"All documents validated. Starting compilation of {len(document_model)} documents..."
    )

    results = [compile_document(doc, output_dir) for doc in document_model]

    failure_count = results.count(False)
    logging.info("--------------------")
    logging.info(
        f"Build Finished. Summary: {len(results) - failure_count} succeeded, {failure_count} failed."
    )
    logging.info("--------------------")

    if failure_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
