import os
import sys
import logging
import shutil
import argparse
import posixpath
from pathlib import Path
from collections import defaultdict
from typing import List
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

        if item.endswith(".template.html"):
            logging.debug(f"Skipping template: {item}")
            continue

        if os.path.isdir(source_item):
            shutil.copytree(source_item, dest_item, dirs_exist_ok=True)
        else:
            shutil.copy2(source_item, dest_item)


def _format_group_name(group_dir_name: str) -> str:
    """Formats 'XX-name_with_underscores' -> 'Name With Underscores'"""
    try:
        name_part = group_dir_name.split("-", 1)[1]
        words = [word.capitalize() for word in name_part.split("_")]
        return " ".join(words)
    except Exception:
        logging.warning(f"Could not format group name: {group_dir_name}")
        return group_dir_name


def _group_sort_key(group_dir_name: str):
    """Sorts '01-' first, then all others by number descending."""
    try:
        num = int(group_dir_name.split("-", 1)[0])
        if num == 1:
            return (0, 0)
        return (1, -num)
    except Exception:
        return (2, 0)  # Fallback for non-numeric groups


def _subgroup_sort_key(subgroup_name: str) -> int:
    """Sorts by 'esterna', 'interna', 'slides'."""
    order = {"esterna": 0, "interna": 1, "slides": 2}
    return order.get(subgroup_name, 99)  # Fallback


def html_from_docmodel(
    document_model: List[docs_lib.Document], docs_folder: str
) -> str:
    """Returns the generated HTML to render links to documents contained in docmodel"""

    # 1. Group documents by their full group directory name and subgroup
    # We get the group name (e.g., '11-candidatura') from the source path,
    # as the 'doc.group' is just the number ('11').
    grouped_docs = defaultdict(lambda: defaultdict(list))
    for doc in document_model:
        try:
            group_dir_name = Path(doc.source).parts[1]
            grouped_docs[group_dir_name][doc.subgroup].append(doc)
        except IndexError:
            logging.warning(f"Could not parse group from doc source: {doc.source}")

    if not grouped_docs:
        return "<p>No documents found.</p>"

    html_lines = []

    sorted_groups = sorted(grouped_docs.keys(), key=_group_sort_key)

    for group_name in sorted_groups:
        subgroups = grouped_docs[group_name]

        html_lines.append(f"<h1>{_format_group_name(group_name)}</h1>")

        sorted_subgroups = sorted(subgroups.keys(), key=_subgroup_sort_key)

        for subgroup_name in sorted_subgroups:
            docs_list = subgroups[subgroup_name]

            html_lines.append(f"<h2>{subgroup_name.capitalize()}</h2>")
            html_lines.append("<ul>")

            for doc in sorted(
                docs_list, key=lambda d: d.last_modified_date, reverse=True
            ):
                # Use posixpath for web URLs (forward slashes)
                link_path = posixpath.join(docs_folder, doc.output)
                link_text = f"{doc.metadata["title"]} (v{doc.latest_version} / {doc.last_modified_date})"
                html_lines.append(f'  <li><a href="{link_path}">{link_text}</a></li>')

            html_lines.append("</ul>")

    return "\n".join(html_lines)


def populate_template(template_path, output_path, html_to_inject):
    """Injects the generated HTML into the template file."""
    logging.info(f"Populating template '{template_path}'...")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
    except FileNotFoundError:
        logging.critical(f"Template file not found: '{template_path}'")
        sys.exit(1)

    placeholder = "{{ static-content }}"
    if placeholder not in template_content:
        logging.critical(
            f"Placeholder '{placeholder}' not found in template. Aborting."
        )
        sys.exit(1)

    final_html = template_content.replace(placeholder, html_to_inject)

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_html)
        logging.info(f"Successfully wrote final HTML to '{output_path}'")
    except IOError as e:
        logging.critical(f"Failed to write final HTML: {e}")
        sys.exit(1)


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

    # Discover documents from the default 'docs/' directory
    document_model = docs_lib.discover_documents("docs")
    logging.debug(f"Found {len(document_model)} documents.")

    os.makedirs(args.outdir, exist_ok=True)

    copy_static_assets(args.site_dir, args.outdir)

    html = html_from_docmodel(document_model, args.docs_folder)

    template_file = os.path.join(args.site_dir, "index.template.html")
    output_html = os.path.join(args.outdir, "index.html")
    populate_template(template_file, output_html, html)

    logging.info("Static site generation complete.")


if __name__ == "__main__":
    main()
