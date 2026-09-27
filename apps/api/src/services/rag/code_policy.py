"""
Code Repository & Local Folder Indexing Policy and Diagnostics.

Defines:
- Explicit allow/deny lists for file extensions and vendor directories.
- Byte and file count budgets.
- Structured skip reasons.
- Ingestion diagnostics container.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


class SkipReason:
    BINARY_OR_NON_TEXT = "binary_or_non_text"
    FILE_TOO_LARGE = "file_too_large"
    TOTAL_CONTEXT_BUDGET_EXCEEDED = "total_context_budget_exceeded"
    DEPENDENCY_OR_VENDOR_DIRECTORY = "dependency_or_vendor_directory"
    GENERATED_OR_MINIFIED_FILE = "generated_or_minified_file"
    UNSUPPORTED_EXTENSION = "unsupported_extension"
    INACCESSIBLE_OR_FETCH_FAILED = "inaccessible_or_fetch_failed"
    SECRET_OR_SENSITIVE_CONTENT_POLICY = "secret_or_sensitive_content_policy"
    TREE_TRUNCATED_OR_NOT_ENUMERATED = "tree_truncated_or_not_enumerated"


@dataclass
class IndexingPolicy:
    """Configurable boundaries for code ingestion."""
    policy_name: str = "default_rag_v1"
    max_file_bytes: int = 100 * 1024         # 100 KB max per file
    max_total_bytes: int = 5 * 1024 * 1024   # 5 MB total repository content budget
    max_files_count: int = 60                # Max 60 source files per ingestion run
    allowed_extensions: Set[str] = field(default_factory=lambda: {
        ".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".json", ".yaml", ".yml", ".md", ".toml"
    })
    denied_directories: Set[str] = field(default_factory=lambda: {
        "node_modules", "dist", "build", "target", "vendor", ".venv", "venv",
        ".next", "__pycache__", ".git", ".github", ".husky", ".turbo"
    })
    denied_filenames: Set[str] = field(default_factory=lambda: {
        "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "cargo.lock", "poetry.lock"
    })
    binary_extensions: Set[str] = field(default_factory=lambda: {
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
        ".woff", ".woff2", ".ttf", ".eot",
        ".zip", ".tar", ".gz", ".7z",
        ".exe", ".dll", ".so", ".dylib", ".bin", ".wasm", ".pyc"
    })


@dataclass
class IngestionDiagnostics:
    """Safe aggregate metrics and provenance details."""
    total_discovered_files: int = 0
    indexed_files: int = 0
    skipped_files: int = 0
    is_partial: bool = False
    warning: Optional[str] = None
    skip_reason_counts: Dict[str, int] = field(default_factory=dict)
    total_indexed_bytes: int = 0
    total_sanitized_files: int = 0
    requested_ref: Optional[str] = None
    resolved_commit_sha: Optional[str] = None
    tree_sha: Optional[str] = None
    policy_name: str = "default_rag_v1"

    def record_skip(self, reason: str):
        self.skipped_files += 1
        self.skip_reason_counts[reason] = self.skip_reason_counts.get(reason, 0) + 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_discovered_files": self.total_discovered_files,
            "indexed_files": self.indexed_files,
            "skipped_files": self.skipped_files,
            "is_partial": self.is_partial,
            "warning": self.warning,
            "skip_reason_counts": self.skip_reason_counts,
            "total_indexed_bytes": self.total_indexed_bytes,
            "total_sanitized_files": self.total_sanitized_files,
            "requested_ref": self.requested_ref,
            "resolved_commit_sha": self.resolved_commit_sha,
            "tree_sha": self.tree_sha,
            "policy_name": self.policy_name,
        }
