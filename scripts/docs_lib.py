import yaml
import subprocess
import os
import sys
import logging
from dataclasses import dataclass
from typing import List, Dict, Set, Optional


@dataclass
class Document:
    """Represents a single, validated, and enriched document."""

    title: str
    source: str
    output: str
    group: str
    changelog_path: str
    changelog: List[Dict]
    subfiles: Set[str]
    latest_version: int
    last_modified_date: str


class FileLoader:
    """Abstract base for file content loaders."""

    def get_content(self, file_path: str) -> Optional[str]:
        raise NotImplementedError("Subclasses must implement this method.")


class LocalFileLoader(FileLoader):
    """Loads file content from the local filesystem."""

    def get_content(self, file_path: str) -> Optional[str]:
        logging.debug(f"Loading local file: '{file_path}'")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logging.error(f"File not found: '{file_path}'")
            return None


class GitFileLoader(FileLoader):
    """Loads file content from a specific git branch."""

    def __init__(self, branch: str):
        self.branch = branch

    def get_content(self, file_path: str) -> Optional[str]:
        logging.debug(f"Loading '{file_path}' from git branch '{self.branch}'")
        try:
            command = ["git", "show", f"{self.branch}:{file_path}"]
            result = subprocess.run(
                command, capture_output=True, text=True, check=True, encoding="utf-8"
            )
            return result.stdout
        except subprocess.CalledProcessError:
            logging.error(f"File '{file_path}' not found in branch '{self.branch}'.")
            return None


def load_documents_model(manifest_path="manifest.yaml") -> List[Document]:
    """Factory function to build the document model from local files."""

    logging.info("Building documents model from local files...")
    local_loader = LocalFileLoader()
    manifest_content = local_loader.get_content(manifest_path)
    if not manifest_content:
        logging.critical(f"Could not load local manifest at '{manifest_path}'.")
        sys.exit(1)

    return _build_model(yaml.safe_load(manifest_content), local_loader)


def load_model_from_git(
    remote_branch_name: str, manifest_path="manifest.yaml"
) -> List[Document]:
    """Factory function to build the document model from a git branch."""

    logging.info(f"Building documents model from git branch '{remote_branch_name}'...")
    git_loader = GitFileLoader(remote_branch_name)
    manifest_content = git_loader.get_content(manifest_path)
    if not manifest_content:
        logging.critical(
            f"Could not load manifest from git branch '{remote_branch_name}'."
        )
        sys.exit(1)

    return _build_model(yaml.safe_load(manifest_content), git_loader)


def _build_model(manifest_data: Dict, loader: FileLoader) -> List[Document]:
    """
    Generic core logic to build the model from manifest data using a provided loader.
    """

    if "documents" not in manifest_data:
        logging.critical("Manifest is missing the required 'documents' key.")
        sys.exit(1)

    documents_list = manifest_data["documents"]
    if not documents_list:
        logging.warning("Manifest 'documents' list is empty. Nothing to build.")
        return []

    document_model = [
        _process_document_entry(entry, loader) for entry in documents_list
    ]

    if None in document_model:
        logging.critical("Model building failed due to validation errors.")
        sys.exit(1)

    logging.info(f"Successfully built a model with {len(document_model)} documents.")
    return document_model


def _process_document_entry(entry: Dict, loader: FileLoader) -> Optional[Document]:
    """
    Takes a single manifest entry and transforms it into a Document object,
    validating each step using the provided loader.
    """

    if not _validate_manifest_entry(entry):
        return None

    source_path = entry["source"]
    changelog_path = _get_changelog_path(source_path)

    changelog_content = loader.get_content(changelog_path)
    if changelog_content is None:
        logging.error(
            f"Validation failed for '{entry['title']}': Could not load changelog at '{changelog_path}'."
        )
        return None

    changelog_data = _parse_yaml_content(
        changelog_content, changelog_path, entry["title"]
    )
    if not changelog_data or not _validate_changelog_structure(
        changelog_data, changelog_path, entry["title"]
    ):
        return None

    versions = [c["version"] for c in changelog_data]
    if not _validate_version_sequence(versions, changelog_path, entry["title"]):
        return None

    subfiles = _find_associated_typ_files(source_path)

    return Document(
        title=entry["title"],
        source=entry["source"],
        output=entry["output"],
        group=entry["group"],
        changelog_path=changelog_path,
        changelog=changelog_data,
        subfiles=subfiles,
        latest_version=changelog_data[0]["version"],
        last_modified_date=changelog_data[0]["date"],
    )


def _get_changelog_path(source_path: str) -> str:
    """Given a source path, calculates the path of its changelog."""
    if not source_path:
        return ""
    base_name = os.path.splitext(source_path)[0]
    return f"{base_name}.changelog.yaml"


def _find_associated_typ_files(source_path: str) -> Set[str]:
    """Finds all .typ files in a source file's directory and subdirectories."""
    subfiles = set()
    source_dir = os.path.dirname(source_path) or "."

    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".typ"):
                file_path = os.path.join(root, file)
                normalized_path = file_path.replace(os.path.sep, "/")
                subfiles.add(normalized_path)
    return subfiles


def _parse_yaml_content(content: str, file_path: str, doc_title: str) -> Optional[list]:
    """Safely parses YAML content from a string."""
    try:
        data = yaml.safe_load(content)
        if not data:
            logging.error(
                f"Validation failed for '{doc_title}': File '{file_path}' is empty."
            )
            return None
        return data
    except yaml.YAMLError as e:
        logging.error(
            f"Validation failed for '{doc_title}': Could not parse YAML in '{file_path}': {e}"
        )
        return None


def _validate_manifest_entry(entry: Dict) -> bool:
    """Validates the presence of required keys in a manifest entry."""
    required_keys = ["title", "source", "output", "group"]
    for key in required_keys:
        if not entry.get(key):
            logging.error(
                f"Invalid manifest entry: Missing or empty key '{key}'. Entry: {entry}"
            )
            return False
    return True


def _validate_changelog_structure(data: List, path: str, title: str) -> bool:
    """Validates the internal structure of a changelog (keys, types)."""
    if not isinstance(data, list):
        logging.error(
            f"Changelog error for '{title}': File '{path}' must be a YAML list."
        )
        return False

    required_keys = ["version", "date", "authors", "verifiers", "description"]
    for i, entry in enumerate(data, 1):
        if not isinstance(entry, dict):
            logging.error(
                f"Changelog error for '{title}': Entry #{i} in '{path}' is not a dictionary."
            )
            return False
        for key in required_keys:
            if key not in entry:
                logging.error(
                    f"Changelog error for '{title}': Entry #{i} is missing key '{key}'."
                )
                return False
        if not isinstance(entry.get("version"), int):
            logging.error(
                f"Changelog error for '{title}': Entry #{i} has a non-integer version."
            )
            return False
    return True


def _validate_version_sequence(versions: List[int], path: str, title: str) -> bool:
    """Validates that a list of versions is sorted and has no gaps."""
    if not versions:
        return True
    if versions != sorted(versions, reverse=True):
        logging.error(
            f"Changelog error for '{title}': Versions in '{path}' are not sorted descending. Found: {versions}"
        )
        return False

    n = len(versions)
    expected = list(range(n, 0, -1))
    if versions != expected:
        logging.error(
            f"Changelog error for '{title}': Versions in '{path}' have gaps or are not sequential."
        )
        logging.error(f"  Expected: {expected}")
        logging.error(f"  Found:    {versions}")
        return False

    return True
