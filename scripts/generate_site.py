import os
import sys
import logging
import shutil
import argparse
from collections import defaultdict

import docs_lib


def setup_logging():
    """Configures logging."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def copy_static_assets(source_dir, dest_dir):
    """Copies all files from the source site directory to the destination."""
    logging.info(f"Copying static assets from '{source_dir}' to '{dest_dir}'...")
    if not os.path.isdir(source_dir):
        logging.critical(f"Source site directory '{source_dir}' not found.")
        sys.exit(1)

    for item in os.listdir(source_dir):
        source_item = os.path.join(source_dir, item)
        dest_item = os.path.join(dest_dir, item)
        if os.path.isdir(source_item):
            shutil.copytree(source_item, dest_item, dirs_exist_ok=True)
        elif not item.endswith(".template.html"):
            shutil.copy2(source_item, dest_item)


def generate_html_links(
    document_model: list[docs_lib.Document], docs_folder: str
) -> dict:
    """Groups documents and generates HTML link snippets."""
    grouped_links = defaultdict(list)

    for doc in document_model:
        link = f'<a href="{docs_folder}/{doc.output}" target="_blank">{doc.title} (v{doc.latest_version})</a>'
        grouped_links[doc.group.upper()].append(link)

    return grouped_links


def populate_template(template_path, output_path, links: dict):
    """Injects the generated HTML links into the template file."""
    logging.info(f"Populating template '{template_path}'...")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
    except FileNotFoundError:
        logging.critical(f"Template file '{template_path}' not found.")
        sys.exit(1)

    final_html = template_content
    for group, link_html_list in links.items():
        marker = f"<!--{group}_LIST_MARKER-->"
        html_content = (
            "\n".join(link_html_list)
            if link_html_list
            else '<a href="#">Nessun documento</a>'
        )
        final_html = final_html.replace(marker, html_content)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html)
    logging.info(f"Successfully generated final HTML at '{output_path}'.")


def main():
    """Main function to orchestrate the site generation process."""
    setup_logging()
    parser = argparse.ArgumentParser(
        description="Generate the static site with document links."
    )
    parser.add_argument(
        "--site-dir", default="site", help="Source directory of the website."
    )
    parser.add_argument(
        "--outdir", default="dist", help="Output directory for the final website."
    )
    parser.add_argument(
        "--docs-folder",
        default="docs",
        help="Subfolder for compiled PDF documents.",
    )
    args = parser.parse_args()

    document_model = docs_lib.load_documents_model()

    os.makedirs(args.outdir, exist_ok=True)

    copy_static_assets(args.site_dir, args.outdir)

    grouped_links = generate_html_links(document_model, args.docs_folder)

    template_file = os.path.join(args.site_dir, "index.template.html")
    output_html = os.path.join(args.outdir, "index.html")
    populate_template(template_file, output_html, grouped_links)

    logging.info("Static site generation complete.")


if __name__ == "__main__":
    main()
