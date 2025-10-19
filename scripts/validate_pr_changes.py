import subprocess
import os
import sys
import logging

import docs_lib

BASE_BRANCH = "origin/main"


def setup_logging():
    """Configures logging."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_changed_files():
    """Gets the set of files changed in this PR compared to the base branch."""
    logging.debug(f"Checking for changed files against '{BASE_BRANCH}'...")
    try:
        command = ["git", "diff", "--name-only", BASE_BRANCH, "HEAD"]
        result = subprocess.run(
            command, capture_output=True, text=True, check=True, encoding="utf-8"
        )
        files = {
            f.replace(os.path.sep, "/") for f in result.stdout.strip().splitlines()
        }
        logging.info(f"Found {len(files)} changed files.")
        logging.debug(f"Changed files: {files}")
        return files
    except subprocess.CalledProcessError as e:
        logging.critical(f"Failed to run 'git diff': {e.stderr}")
        sys.exit(1)


def compare_models(
    new_model: list[docs_lib.Document],
    old_model: list[docs_lib.Document],
    changed_files: set,
):
    """
    Compares the new (PR) and old (main) document models to validate changes.
    """
    logging.info("Comparing document models to validate PR changes...")
    old_docs_map = {doc.source: doc for doc in old_model}
    errors_found = False

    for new_doc in new_model:
        # Check if any of this document's files (.typ or .changelog) were modified
        files_to_check = new_doc.subfiles.union({new_doc.changelog_path})
        modified_files_for_this_doc = files_to_check.intersection(changed_files)

        if not modified_files_for_this_doc:
            # No files related to this document were changed, so we skip it.
            continue

        logging.info(f"Document '{new_doc.title}' was modified. Validating changes...")
        logging.debug(f"  Modified files: {modified_files_for_this_doc}")

        old_doc = old_docs_map.get(new_doc.source)

        if old_doc is None:
            # This is a new document
            if new_doc.latest_version != 1:
                logging.error(
                    f"Validation failed for NEW document '{new_doc.title}': "
                    f"Latest version must be 1, but found {new_doc.latest_version}."
                )
                errors_found = True
            else:
                logging.info(
                    f"  SUCCESS: New document '{new_doc.title}' correctly starts at version 1."
                )
        else:
            # This is an existing document, compare versions
            if new_doc.latest_version != old_doc.latest_version + 1:
                logging.error(
                    f"Validation failed for '{new_doc.title}': Invalid version increment."
                )
                logging.error(
                    f"  Version on '{BASE_BRANCH}': {old_doc.latest_version}. "
                    f"Version in PR: {new_doc.latest_version}. "
                    f"Expected: {old_doc.latest_version + 1}."
                )
                errors_found = True
            else:
                logging.info(
                    f"  SUCCESS: Document '{new_doc.title}' correctly incremented version "
                    f"from {old_doc.latest_version} to {new_doc.latest_version}."
                )

    return not errors_found


def main():
    """Main function to orchestrate the PR validation process."""
    setup_logging()

    # Load both models to get a "before" and "after" snapshot
    logging.info(f"Loading OLD model from '{BASE_BRANCH}'...")
    old_model = docs_lib.load_model_from_git(BASE_BRANCH)

    logging.info("Loading NEW model from current PR branch...")
    new_model = docs_lib.load_documents_model()

    # Get the set of physically changed files
    changed_files = get_changed_files()

    # Perform the semantic comparison
    is_valid = compare_models(new_model, old_model, changed_files)

    if not is_valid:
        logging.critical("PR validation failed. See errors above.")
        sys.exit(1)

    logging.info("All PR validation checks passed successfully!")


if __name__ == "__main__":
    main()
