#!/usr/bin/env python3
"""
Script to automatically increment version in __init__.py when merging into main.

This script compares the version between main branch and source branch
and increments the patch version if they are identical.
"""

import argparse
import os
import re
import subprocess
import sys
from typing import Tuple


def get_version_from_file(file_path: str) -> str:
    """
    Extract version string from __init__.py file.

    Args:
        file_path: Path to the __init__.py file

    Returns:
        Version string (e.g., "1.0.12")

    Raises:
        RuntimeError: If version string not found
        FileNotFoundError: If file doesn't exist
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Version file not found: {file_path}")

    # Match __version__ = "x.y.z" pattern
    version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if not version_match:
        raise RuntimeError(f"No __version__ found in {file_path}")

    return version_match.group(1)


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """
    Parse semantic version string into major, minor, patch components.

    Args:
        version_str: Version string like "1.0.12"

    Returns:
        Tuple of (major, minor, patch) as integers

    Raises:
        ValueError: If version format is invalid
    """
    parts = version_str.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version_str}")

    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        raise ValueError(f"Invalid version format: {version_str}")


def increment_patch_version(version_str: str) -> str:
    """
    Increment the patch version component.

    Args:
        version_str: Current version string like "1.0.12"

    Returns:
        New version string with incremented patch version
    """
    major, minor, patch = parse_version(version_str)
    return f"{major}.{minor}.{patch + 1}"


def update_version_in_file(file_path: str, new_version: str) -> None:
    """
    Update the version string in __init__.py file.

    Args:
        file_path: Path to the __init__.py file
        new_version: New version string to set
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace the version string, preserving the original format
    new_content = re.sub(
        r'(__version__\s*=\s*["\'])([^"\']+)(["\'])',
        rf"\g<1>{new_version}\g<3>",
        content,
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Updated version in {file_path} to {new_version}")


def get_main_branch_version(init_file_path: str) -> str:
    """
    Get the version from the main branch.

    Args:
        init_file_path: Relative path to __init__.py file

    Returns:
        Version string from main branch

    Raises:
        subprocess.CalledProcessError: If git command fails
    """
    # Try different ways to reference main branch
    main_refs = ["origin/main", "main"]

    # Support for legacy path structure (thermostatsupervisor -> src rename)
    possible_paths = [init_file_path]
    if init_file_path.startswith("src/"):
        # Try legacy path if current path starts with src/
        legacy_path = init_file_path.replace("src/", "thermostatsupervisor/", 1)
        possible_paths.append(legacy_path)
    elif init_file_path.startswith("thermostatsupervisor/"):
        # Try new path if current path starts with thermostatsupervisor/
        new_path = init_file_path.replace(
            "thermostatsupervisor/", "src/", 1
        )
        possible_paths.append(new_path)

    for main_ref in main_refs:
        # First try fetching main branch if not available
        if main_ref == "origin/main":
            try:
                subprocess.run(
                    ["git", "fetch", "origin", "main"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
            except subprocess.CalledProcessError:
                pass  # Might already be available

        # Try each possible path
        for file_path in possible_paths:
            try:
                # Get file content from main branch
                result = subprocess.run(
                    ["git", "show", f"{main_ref}:{file_path}"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                content = result.stdout

                # Extract version from content
                version_match = re.search(
                    r'__version__\s*=\s*["\']([^"\']+)["\']', content
                )
                if not version_match:
                    raise RuntimeError(
                        f"No __version__ found in main branch {file_path}"
                    )

                print(f"Found version in main branch using path: {file_path}")
                return version_match.group(1)

            except subprocess.CalledProcessError:
                continue  # Try next path or reference

    raise RuntimeError(
        f"Failed to get main branch version from any reference: {main_refs}, "
        f"tried paths: {possible_paths}"
    )


def run_git_command(cmd: list) -> subprocess.CompletedProcess:
    """
    Run a git command and handle errors.

    Args:
        cmd: Git command as list of strings

    Returns:
        Completed process result

    Raises:
        subprocess.CalledProcessError: If command fails
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {' '.join(cmd)}")
        print(f"Error: {e.stderr}")
        raise


def main():
    """Main function to handle version increment logic."""
    parser = argparse.ArgumentParser(
        description="Automatically increment version if identical to main"
    )
    parser.add_argument(
        "--init-file",
        default="src/__init__.py",
        help="Path to __init__.py file",
    )
    parser.add_argument(
        "--commit", action="store_true", help="Commit and push the version change"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    # Ensure we're in a git repository
    if not os.path.exists(".git"):
        print("Error: Not in a git repository")
        sys.exit(1)

    # Check if init file exists
    if not os.path.exists(args.init_file):
        print(f"Error: Version file not found: {args.init_file}")
        sys.exit(1)

    try:
        # Get current branch version
        current_version = get_version_from_file(args.init_file)
        print(f"Current branch version: {current_version}")

        # Get main branch version
        main_version = get_main_branch_version(args.init_file)
        print(f"Main branch version: {main_version}")

        # Compare versions
        if current_version == main_version:
            new_version = increment_patch_version(current_version)
            print(f"Versions are identical, incrementing to: {new_version}")

            if args.dry_run:
                print("DRY RUN: Would increment version and commit changes")
                return

            # Update version in file
            update_version_in_file(args.init_file, new_version)

            if args.commit:
                # Configure git user for GitHub Actions
                run_git_command(
                    ["git", "config", "--local", "user.email", "action@github.com"]
                )
                run_git_command(
                    ["git", "config", "--local", "user.name", "GitHub Action"]
                )

                # Stage and commit the change
                run_git_command(["git", "add", args.init_file])
                run_git_command(
                    ["git", "commit", "-m", f"Auto-increment version to {new_version}"]
                )

                print(f"Committed version increment to {new_version}")

        else:
            print("Versions are different, no increment needed")

            # Check if current version is newer
            try:
                current_parts = parse_version(current_version)
                main_parts = parse_version(main_version)

                if current_parts <= main_parts:
                    print("Warning: Current version is not newer than main")
                    sys.exit(1)

            except ValueError as e:
                print(f"Warning: Could not compare versions: {e}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
