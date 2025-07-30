#!/usr/bin/env -S uv run --script
# /// script
# dependencies=[
#     "copier",
#     "click",
# ]
# ///

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, List
import click
import copier


def run_git_command(
    cmd: List[str], cwd: Optional[Path] = None
) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the result."""
    click.echo(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=True
        )
        return result
    except subprocess.CalledProcessError as e:
        click.echo(f"Command failed with exit code {e.returncode}", err=True)
        click.echo(f"stdout: {e.stdout}", err=True)
        click.echo(f"stderr: {e.stderr}", err=True)
        sys.exit(1)


def get_merge_base_with_main(script_dir: Path) -> str:
    """Get merge base with main as default revision."""
    try:
        result = run_git_command(["git", "merge-base", "HEAD", "main"], cwd=script_dir)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        # Fallback to main if merge-base fails
        click.echo("Warning: Could not determine merge base with main, using 'main'")
        return "main"


def get_git_tracked_files(directory: Path, respect_gitignore: bool = True) -> set[Path]:
    """Get set of files that would be tracked by git (optionally respecting gitignore)."""
    
    # Files to always ignore
    ignored_files = {".copier-answers.yml"}
    
    if not respect_gitignore:
        # Just return all files, excluding ignored ones
        tracked_files = set()
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(directory)
                if relative_path.name not in ignored_files:
                    tracked_files.add(relative_path)
        return tracked_files
    
    try:
        # Use git ls-files to get files that git would track
        # This respects .gitignore rules
        result = subprocess.run(
            ["git", "ls-files", "--others", "--cached", "--exclude-standard"],
            cwd=directory,
            capture_output=True,
            text=True,
            check=True
        )
        
        tracked_files = set()
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                file_path = directory / line.strip()
                relative_path = Path(line.strip())
                if file_path.is_file() and relative_path.name not in ignored_files:
                    tracked_files.add(relative_path)
        
        return tracked_files
    except subprocess.CalledProcessError:
        # Fallback: for temp directories (expected), don't respect gitignore
        # For actual directories, warn and use all files
        if "expected" in str(directory):
            return get_git_tracked_files(directory, respect_gitignore=False)
        else:
            click.echo("Warning: Could not determine git-tracked files, using all files")
            return get_git_tracked_files(directory, respect_gitignore=False)


def compare_directories(expected_dir: Path, actual_dir: Path) -> List[str]:
    """Compare two directories and return list of files that differ, respecting gitignore."""
    differences = []
    
    # Get files in both directories
    # For expected (temp) directory: get all files (no gitignore)
    # For actual directory: respect gitignore
    expected_files = get_git_tracked_files(expected_dir, respect_gitignore=False) if expected_dir.exists() else set()
    actual_files = get_git_tracked_files(actual_dir, respect_gitignore=True) if actual_dir.exists() else set()
    
    # Check for files only in expected
    for file_path in expected_files - actual_files:
        differences.append(f"Missing file: {file_path}")
    
    # Check for files only in actual
    for file_path in actual_files - expected_files:
        differences.append(f"Extra file: {file_path}")
    
    # Check for files that exist in both but differ
    for file_path in expected_files & actual_files:
        expected_file = expected_dir / file_path
        actual_file = actual_dir / file_path
        
        # Compare file contents
        try:
            with open(expected_file, "r", encoding="utf-8") as f:
                expected_content = f.read()
            with open(actual_file, "r", encoding="utf-8") as f:
                actual_content = f.read()
            
            if expected_content != actual_content:
                differences.append(f"Content differs: {file_path}")
        except (UnicodeDecodeError, PermissionError):
            # For binary files or permission issues, use basic comparison
            if expected_file.stat().st_size != actual_file.stat().st_size:
                differences.append(f"Content differs (binary): {file_path}")
    
    return differences


def compare_with_expected_materialized(
    script_dir: Path, check_mode: bool = False
) -> None:
    """Compare current test-proj with freshly generated template."""
    click.echo("Generating expected materialized version from current template...")

    with tempfile.TemporaryDirectory() as temp_dir:
        expected_proj = Path(temp_dir) / "expected-proj"

        # Generate expected materialized version
        copier.run_copy(
            src_path=str(script_dir),
            dst_path=str(expected_proj),
            data={"project_name": "test-proj", "project_title": "Test Project"},
            unsafe=True,
        )

        # Compare expected vs actual
        test_proj_dir = script_dir / "test-proj"
        differences = compare_directories(expected_proj, test_proj_dir)

        if not differences:
            click.echo("✓ test-proj matches expected template output")
            return

        click.echo(
            f"\n❌ Found {len(differences)} differences between expected and actual:"
        )
        for diff in differences:
            click.echo(f"  {diff}")

        files_to_copy = []
        files_needing_manual_fix = []

        # For files that differ in content, show detailed diff and categorize
        click.echo("\nDetailed differences:")
        for diff in differences:
            if diff.startswith("Content differs: "):
                file_path = diff[len("Content differs: ") :]
                expected_file = expected_proj / file_path
                actual_file = test_proj_dir / file_path

                # Determine corresponding template file path
                template_file_path = map_materialized_to_template_path(
                    script_dir, str(file_path)
                )
                template_file = script_dir / template_file_path

                click.echo(f"\n--- Expected (from template): {file_path}")
                click.echo(f"+++ Actual (in test-proj): {file_path}")

                # Use git diff for better output
                try:
                    result = subprocess.run(
                        [
                            "git",
                            "diff",
                            "--no-index",
                            str(expected_file),
                            str(actual_file),
                        ],
                        capture_output=True,
                        text=True,
                        cwd=script_dir,
                    )
                    # git diff returns 1 when files differ, which is expected
                    if result.stdout:
                        # Skip the file headers and show just the content diff
                        lines = result.stdout.split("\n")
                        for line in lines[4:]:  # Skip first 4 lines (headers)
                            if line.strip():
                                click.echo(f"  {line}")
                except subprocess.CalledProcessError:
                    # Fallback to basic diff indication
                    click.echo("  (Files differ)")

                # Categorize for fixing
                if template_file_path.endswith(".jinja"):
                    files_needing_manual_fix.append((file_path, template_file_path))
                else:
                    files_to_copy.append(
                        (str(file_path), template_file_path, actual_file, template_file)
                    )

            elif diff.startswith("Extra file: "):
                file_path = diff[len("Extra file: ") :]
                actual_file = test_proj_dir / file_path

                # Determine corresponding template file path
                template_file_path = map_materialized_to_template_path(
                    script_dir, str(file_path)
                )
                template_file = script_dir / template_file_path

                click.echo(f"\nExtra file in test-proj: {file_path}")

                # Categorize for fixing
                if template_file_path.endswith(".jinja"):
                    files_needing_manual_fix.append((file_path, template_file_path))
                else:
                    files_to_copy.append(
                        (str(file_path), template_file_path, actual_file, template_file)
                    )

        # Provide guidance and optionally fix
        if check_mode:
            click.echo("\nTo fix template files, you can:")
            click.echo("1. Copy non-templated files: run fix_template --fix")
            click.echo(
                "2. Manually update .jinja files based on the differences shown above"
            )
        else:
            if files_to_copy:
                click.echo(
                    f"\nCopying {len(files_to_copy)} non-templated files back to template:"
                )
                for (
                    relative_path,
                    template_path,
                    actual_file,
                    template_file,
                ) in files_to_copy:
                    click.echo(f"Copying {relative_path} → {template_path}")
                    template_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(actual_file, template_file)

            if files_needing_manual_fix:
                click.echo(
                    f"\n⚠️  {len(files_needing_manual_fix)} templated files need manual resolution:"
                )
                for materialized_path, template_path in files_needing_manual_fix:
                    click.echo(f"  {materialized_path} → {template_path}")


def fix_template_from_materialized(script_dir: Path, revision: str) -> None:
    """Fix template files by copying back files changed since revision from materialized test-proj."""

    # Get list of files changed since the specified revision in test-proj
    git_diff_name_only: subprocess.CompletedProcess[str] = run_git_command(
        ["git", "diff", "--name-only", revision, "--", "test-proj/"], cwd=script_dir
    )

    if not git_diff_name_only.stdout.strip():
        click.echo(f"No changes in test-proj since {revision}")
        return

    changed_files: List[str] = git_diff_name_only.stdout.strip().split("\n")

    for file_path in changed_files:
        # Remove test-proj/ prefix to get relative path within the project
        if not file_path.startswith("test-proj/"):
            continue

        relative_path: str = file_path[len("test-proj/") :]
        materialized_file: Path = script_dir / file_path

        # Skip files that don't exist (deleted files)
        if not materialized_file.exists():
            click.echo(f"Skipping deleted file: {relative_path}")
            continue

        # Handle template path mapping
        template_file_path: str = map_materialized_to_template_path(
            script_dir, relative_path
        )
        template_file: Path = script_dir / template_file_path

        if template_file_path.endswith(".jinja"):
            # Show warning for .jinja files that need manual resolution
            click.echo(f"⚠️  Manual resolution required: {template_file_path}")
            click.echo(f"   Materialized file: {relative_path}")

            # Show diff for just this file since the revision
            git_diff: subprocess.CompletedProcess[str] = run_git_command(
                ["git", "diff", revision, "--", file_path], cwd=script_dir
            )
            if git_diff.stdout.strip():
                click.echo("   Changes since revision:")
                for diff_line in git_diff.stdout.split("\n"):
                    click.echo(f"   {diff_line}")
            click.echo()
        else:
            # Copy non-templated files back
            click.echo(f"Copying {relative_path} → {template_file_path}")
            template_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(materialized_file, template_file)


def map_materialized_to_template_path(script_dir: Path, materialized_path: str) -> str:
    """Map a materialized file path back to its template path."""
    path_parts: tuple[str, ...] = Path(materialized_path).parts

    # Handle the special case of src/test_proj/ → src/{{ project_name_snake }}/
    if len(path_parts) >= 2 and path_parts[0] == "src" and path_parts[1] == "test_proj":
        # Replace test_proj with the template variable
        new_parts: tuple[str, ...] = ("src", "{{ project_name_snake }}") + path_parts[
            2:
        ]
        template_path: str = str(Path(*new_parts))

        # Check if a .jinja version exists
        jinja_path: str = template_path + ".jinja"
        if (script_dir / jinja_path).exists():
            return jinja_path
        return template_path

    # For other paths, check if .jinja version exists
    jinja_path: str = materialized_path + ".jinja"
    if (script_dir / jinja_path).exists():
        return jinja_path

    return materialized_path


@click.group()
def cli() -> None:
    """Template validation and fixing tools."""
    pass


def regenerate_test_proj(script_dir: Path) -> None:
    """Regenerate the test-proj directory using copier."""
    # Delete the test-proj directory if it exists
    test_proj_dir: Path = script_dir / "test-proj"
    if test_proj_dir.exists():
        click.echo(f"Deleting {test_proj_dir}")
        shutil.rmtree(test_proj_dir)
    else:
        click.echo(f"Directory {test_proj_dir} does not exist")

    # Run copier to regenerate test-proj
    click.echo("Running copier to regenerate test-proj...")
    copier.run_copy(
        src_path=str(script_dir),
        dst_path=str(test_proj_dir),
        data={"project_name": "test-proj", "project_title": "Test Project"},
        unsafe=True,
    )


def get_script_dir_and_setup() -> Path:
    """Get the script directory and set up working directory. Common setup for all commands."""
    script_dir: Path = Path(__file__).parent.parent
    os.chdir(script_dir)
    click.echo(f"Working directory: {script_dir}")
    return script_dir


def ensure_test_proj_exists(script_dir: Path) -> Path:
    """Ensure test-proj directory exists and return its path."""
    test_proj_dir: Path = script_dir / "test-proj"
    if not test_proj_dir.exists():
        click.echo(
            "Error: test-proj directory does not exist. Run 'regenerate' first.",
            err=True,
        )
        sys.exit(1)
    return test_proj_dir


@cli.command()
def regenerate() -> None:
    """Regenerate test-proj directory using copier."""
    script_dir: Path = get_script_dir_and_setup()

    # Check for uncommitted changes before starting
    click.echo("Checking for uncommitted changes...")
    git_status_check: subprocess.CompletedProcess[str] = run_git_command(
        ["git", "status", "--porcelain"], cwd=script_dir
    )
    if git_status_check.stdout.strip():
        click.echo(
            "Error: Repository has uncommitted changes. Please commit or stash them first.",
            err=True,
        )
        click.echo(git_status_check.stdout)
        sys.exit(1)

    regenerate_test_proj(script_dir)
    click.echo("✓ test-proj regenerated")


@cli.command()
def check_regeneration() -> None:
    """Check if generated files match template (assumes test-proj already exists)."""
    script_dir: Path = get_script_dir_and_setup()

    regenerate_test_proj(script_dir)

    # Check if generated files match template
    click.echo("Checking generated files against template...")
    git_status: subprocess.CompletedProcess[str] = run_git_command(
        ["git", "status", "--porcelain"], cwd=script_dir
    )

    if git_status.stdout.strip():
        click.echo("\n❌ Generated files do not match template!", err=True)
        click.echo("\nFiles that differ:")
        click.echo(git_status.stdout)

        click.echo("\nDifferences:")
        git_diff: subprocess.CompletedProcess[str] = run_git_command(
            ["git", "diff"], cwd=script_dir
        )
        click.echo(git_diff.stdout)

        click.echo(
            "\nTo fix: If these changes look good, likely you just need to run regenerate and commit the changes.",
            err=True,
        )
        sys.exit(1)
    else:
        click.echo("✓ Generated files match template")


@cli.command("check-python")
@click.option("--fix", is_flag=True, help="Fix formatting issues automatically.")
def check_python(fix: bool) -> None:
    """Run Python validation checks on test-proj using hatch."""
    script_dir: Path = get_script_dir_and_setup()
    test_proj_dir: Path = ensure_test_proj_exists(script_dir)

    # Run Python checks with hatch
    click.echo("Running Python validation checks...")
    run_git_command(
        ["uv", "run", "hatch", "run", "all-fix" if fix else "all-check"],
        cwd=test_proj_dir,
    )
    click.echo("✓ Python checks passed")


@cli.command("check-javascript")
@click.option("--fix", is_flag=True, help="Fix formatting issues automatically.")
def check_javascript(fix: bool) -> None:
    """Run TypeScript and format validation checks on test-proj/ui using pnpm."""
    script_dir: Path = get_script_dir_and_setup()
    test_proj_dir: Path = ensure_test_proj_exists(script_dir)
    ui_dir: Path = test_proj_dir / "ui"

    # Check if ui directory exists
    if not ui_dir.exists():
        click.echo(
            "Error: test-proj/ui directory does not exist.",
            err=True,
        )
        sys.exit(1)

    # Run TypeScript checks with pnpm
    click.echo("Running TypeScript validation checks...")
    run_git_command(["pnpm", "run", "all-fix" if fix else "all-check"], cwd=ui_dir)
    click.echo("✓ TypeScript checks passed")


@cli.command()
@click.argument("revision", required=False)
@click.option(
    "--legacy-mode",
    is_flag=True,
    help="Use legacy git-diff based approach instead of expected materialized comparison.",
)
@click.option(
    "--fix",
    is_flag=True,
    help="Automatically copy non-templated files back to template.",
)
def fix_template(revision: Optional[str], legacy_mode: bool, fix: bool) -> None:
    """Fix template files by copying back changes from materialized test-proj.

    By default, compares test-proj with what the current template would generate.
    REVISION is optional and defaults to merge-base with main when using legacy mode.
    """
    script_dir: Path = get_script_dir_and_setup()

    # Check if test-proj exists
    ensure_test_proj_exists(script_dir)

    if legacy_mode:
        # Use the original git-diff based approach
        if revision is None:
            revision = get_merge_base_with_main(script_dir)
            click.echo(f"Using auto-detected revision: {revision}")

        # Validate that the revision exists
        try:
            run_git_command(["git", "rev-parse", "--verify", revision], cwd=script_dir)
        except subprocess.CalledProcessError:
            click.echo(f"Error: Revision '{revision}' not found", err=True)
            sys.exit(1)

        # Fix template files based on changes since revision
        fix_template_from_materialized(script_dir, revision)
    else:
        # Use new expected materialized comparison approach
        if revision is not None:
            click.echo(
                "Warning: revision argument ignored when not using --legacy-mode"
            )

        compare_with_expected_materialized(script_dir, check_mode=fix)


if __name__ == "__main__":
    cli()
