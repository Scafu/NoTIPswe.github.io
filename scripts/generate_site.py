import os
import sys
import logging
import shutil
import argparse
import posixpath
from pathlib import Path, PurePosixPath
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
    logging.info(
        f"Copying static assets from '{source_dir}' to '{dest_dir}'...")
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


''' unused
def _format_group_name(group_dir_name: str) -> str:
    """Formats 'XX-name_with_underscores' -> 'Name With Underscores'"""
    try:
        name_part = group_dir_name.split("-", 1)[1]
        words = [word.capitalize() for word in name_part.split("_")]
        return " ".join(words)
    except Exception:
        logging.warning(f"Could not format group name: {group_dir_name}")
        return group_dir_name
'''


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
    """Sorts by 'esterno', 'interno', 'slides'."""
    order = {"esterno": 0, "interno": 1, "slides": 2}
    return order.get(subgroup_name, 99)  # Fallback

# Table content generation from docs_folder


def html_table_rows_from_docmodel(
    document_model: List[docs_lib.Document], docs_folder: str
) -> str:
    """Generates HTML table rows for documents contained in document_model."""

    # 1. Raggruppa i documenti per directory di gruppo e sottogruppo
    grouped_docs = defaultdict(lambda: defaultdict(list))
    for doc in document_model:
        try:
            group_dir_name = Path(doc.source).parts[1]
            grouped_docs[group_dir_name][doc.subgroup].append(doc)
        except IndexError:
            logging.warning(
                f"Could not parse group from doc source: {doc.source}")

    if not grouped_docs:
        return "<p>No documents found.</p>"

    html_lines = []

    sorted_groups = sorted(grouped_docs.keys(), key=_group_sort_key)

    for group_name in sorted_groups:
        subgroups = grouped_docs[group_name]

        sorted_subgroups = sorted(subgroups.keys(), key=_subgroup_sort_key)

        for subgroup_name in sorted_subgroups:
            docs_list = subgroups[subgroup_name]

            # 1° Version, if we wanna divide the list into 3 section
            # html_lines.append(f"<h2>{subgroup_name.capitalize()}</h2>")
            # html_lines.append('<table class="doc-table">')
            '''html_lines.append("""
                <thead>
                    <tr>
                        <th>Titolo</th>
                        <th>Ultima Versione</th>
                        <th id="download-th">Download</th>
                    </tr>
                </thead>
            """)'''

            for doc in sorted(docs_list, key=lambda d: d.last_modified_date, reverse=True):
                link_path = posixpath.join("..", docs_folder, group_name, subgroup_name, Path(
                    doc.output).stem, Path(doc.output).name)
                title = doc.metadata.get("title", "Untitled")
                version = doc.latest_version
                doc_type = subgroup_name.capitalize()

                # 1° Version
                '''row_html = f"""
                <tr>
                    <td>{title}</td>
                    <td>v{version}.0</td>
                    <td><a href="file.pdf" target="_blank" rel="noopener noreferrer">Preview</a></td>
                    <td>
                        <a href="{link_path}" class="btn-download" download>
                            <span class="icon">&#8681;</span>Download
                        </a>
                    </td>
                </tr>
                """'''
                # 2° Version
                row_html = f"""
                <tr>
                    <td>{title}</td>
                    <td>v{version}.0</td>
                    <td>{doc_type}</td>
                    <td id="download-td">
                    <a href="{link_path}" target="_blank" rel="noopener noreferrer" class="preview-link">
                    <span class="icon" data-icon="visibility"></span><span>Preview</span>
                    </a>
                        <a href="{link_path}" class="btn-download" download>
                            <span class="icon" data-icon="download"></span>Download
                        </a>
                    </td>
                </tr>
                """
                html_lines.append(row_html)

            logging.info(f"Metadata keys: {list(doc.metadata.keys())}")

    return "\n".join(html_lines)


def format_category_name(category_name: str) -> str:
    """In case we have acronymns we have to put here the complete name"""
    mapping = {
        "rtb": "Requirements and Technology Baseline (RTB)",
        "pb": "Product Baseline (PB)"
    }
    return mapping.get(category_name.lower(), category_name.capitalize())


def generate_category_links(template_path, output_path, docs_folder="docs"):
    """
    This function generates the category cards from folder names inside `docs`,
    ignoring folders starting with '00-' and linking to `<categoria>.html`.
    """
    docs_path = Path(docs_folder)
    categories_folders = []

    # Trova tutte le cartelle valide
    for folder in sorted(docs_path.iterdir()):
        if folder.is_dir() and "-" in folder.name:
            if folder.name.startswith("00-"):
                continue
            categories_folders.append(folder.name)

    # Genera l'HTML

    html_snippet = ""
    for cat_folder in categories_folders:
        # Estrai solo la parte dopo il trattino
        category_name = cat_folder.split("-", 1)[1].replace("_", " ")
        display_name = format_category_name(category_name)
        href_name = category_name.lower().replace(
            " ", "_") + ".html"  # es. "rtb" -> "rtb.html"
        num_docs = len(list((docs_path / cat_folder).rglob("*.pdf")))
        html_snippet += f'''
        <a class="category-card" href="{href_name}">
            <h3>{display_name}</h3>
            <p class="doc-count">{num_docs} Documenti</p>
        </a>
        '''

    # Popola il template
    template_content = Path(template_path).read_text(encoding="utf-8")
    populated_content = template_content.replace(
        "<!--CATEGORIES_LIST_MARKER-->", html_snippet)
    Path(output_path).write_text(populated_content, encoding="utf-8")
    print(f"Pagina generata: {output_path}")


def populate_template(template_path, output_path, html_blocks):
    """Injects generated HTML blocks into the template file based on comment markers."""
    logging.info(f"Populating template '{template_path}'...")

    try:
        template_content = Path(template_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        logging.critical(f"Template file not found: '{template_path}'")
        sys.exit(1)

    # Replace each marker like <!--PB_LIST_MARKER-->
    for marker, html_snippet in html_blocks.items():
        placeholder = f"<!--{marker}_LIST_MARKER-->"
        if placeholder in template_content:
            template_content = template_content.replace(
                placeholder, html_snippet)
            logging.info(f"Injected HTML for marker: {marker}")
        else:
            logging.warning(f"Marker '{placeholder}' not found in template.")

    Path(output_path).write_text(template_content, encoding="utf-8")
    logging.info(f"Successfully wrote final HTML to '{output_path}'")


def main():
    """Genera il sito statico con file separati per ciascun gruppo di documenti."""
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Generate the static site with document links."
    )
    parser.add_argument("--site-dir", default="site",
                        help="Directory dei template del sito.")
    parser.add_argument("--outdir", default="dist",
                        help="Directory di output del sito.")
    parser.add_argument("--docs-folder", default="docs",
                        help="Sottocartella dei PDF compilati.")
    args = parser.parse_args()

    # Scopri tutti i documenti
    document_model = docs_lib.discover_documents(args.docs_folder)
    logging.info(f"Trovati {len(document_model)} documenti.")

    # Assicurati che la cartella di output esista
    os.makedirs(args.outdir, exist_ok=True)
    copy_static_assets(args.site_dir, args.outdir)

    # =========================
    # Genera homepage dinamica
    # =========================
    home_template = os.path.join(args.site_dir, "index.template.html")
    home_output = os.path.join(args.outdir, "index.html")

    try:
        Path(home_template).read_text(encoding="utf-8")
    except FileNotFoundError:
        logging.critical(f"Home template not found: '{home_template}'")
        sys.exit(1)

    # Genera dinamicamente la homepage con le categorie
    generate_category_links(
        template_path=home_template,
        output_path=home_output,
        docs_folder=args.docs_folder
    )
    logging.info(f"Homepage generata: {home_output}")

    # ==============================
    # Genera pagine per ogni gruppo
    # ==============================
    template_file = os.path.join(args.site_dir, "template_document.html")

    # Leggi tutte le sottocartelle del docs_folder (es. 01-rtb, 02-pb, ecc.)
    docs_path = Path(args.docs_folder)
    category_folders = [
        f for f in sorted(docs_path.iterdir())
        if f.is_dir() and "-" in f.name and not f.name.startswith("00-")
    ]

    for folder in category_folders:
        # Estrai il nome categoria (es. "01-rtb" → "rtb")
        category_name = folder.name.split("-", 1)[1]
        display_name = format_category_name(category_name)

        # Filtra i documenti che appartengono a questa categoria
        filtered_docs = [
            d for d in document_model if category_name.lower() in d.source.lower()
        ]

        html_rows = html_table_rows_from_docmodel(
            filtered_docs, args.docs_folder)

        # Genera il file HTML di output dinamico (es. rtb.html)
        output_file = os.path.join(
            args.outdir, f"{category_name.lower()}.html")

        html_blocks = {
            "GROUP": display_name,
            "DOCUMENTS": html_rows
        }

        populate_template(template_file, output_file, html_blocks)
        logging.info(f"Pagina generata per {display_name}: {output_file}")

    logging.info("Generazione del sito completata.")


if __name__ == "__main__":
    main()
