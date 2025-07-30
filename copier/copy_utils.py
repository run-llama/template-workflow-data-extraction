#!/usr/bin/env -S uv run --script
# /// script
# dependencies=[
#     "copier",
#     "click",
# ]
# ///

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import click
import copier


def parse_template_variables() -> Dict[str, str]:
    """Parse template variables from copier.yaml."""
    # For this template, we know the main variables
    return {
        "project_name": "test-proj",
        "project_title": "Test Project",
        "project_name_snake": "test_proj",
    }


def find_simple_jinja_patterns(template_line: str) -> List[Tuple[str, str]]:
    """Find simple jinja variable patterns in a template line.

    Returns list of (pattern, variable_name) tuples.
    """
    patterns = []

    # Find {{variable}} patterns
    variable_pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}'
    for match in re.finditer(variable_pattern, template_line):
        patterns.append((match.group(0), match.group(1)))

    # Find {{variable.method()}} patterns (simple transforms)
    transform_pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_().\-\'" ]+)\s*\}\}'
    for match in re.finditer(transform_pattern, template_line):
        patterns.append((match.group(0), match.group(1)))

    return patterns


def evaluate_jinja_expression(expression: str, variables: Dict[str, str]) -> Optional[str]:
    """Safely evaluate simple jinja expressions."""
    try:
        # Handle simple variable references
        if expression in variables:
            return variables[expression]

        # Handle simple method calls on variables
        if '.' in expression:
            var_name = expression.split('.')[0]
            if var_name in variables:
                value = variables[var_name]

                # Handle common string methods
                if ".replace('-', '_')" in expression:
                    return value.replace('-', '_')
                elif ".replace('-', ' ').title()" in expression:
                    return value.replace('-', ' ').title()
                elif ".replace('_', '-')" in expression:
                    return value.replace('_', '-')

        return None
    except Exception:
        return None


def attempt_simple_line_resolution(
    template_line: str,
    expected_line: str,
    actual_line: str,
    variables: Dict[str, str]
) -> Optional[str]:
    """Try to resolve a single line difference by updating jinja variables.

    Returns updated template line if successful, None if too complex.
    """

    # Skip if template line has no jinja patterns
    jinja_patterns = find_simple_jinja_patterns(template_line)
    if not jinja_patterns:
        return None

    # Skip complex jinja (conditionals, loops, etc.)
    if '{%' in template_line or '{#' in template_line:
        return None

    # Try to reverse-engineer what the new variable values should be
    new_template_line = template_line

    for pattern, expression in jinja_patterns:
        expected_value = evaluate_jinja_expression(expression, variables)
        if expected_value is None:
            continue

        # Check if this pattern appears in expected but should be different in actual
        if expected_value in expected_line:
            # Find what it should be in actual_line
            # This is a simple heuristic - look for the same pattern
            expected_parts = expected_line.split(expected_value)
            if len(expected_parts) == 2:
                prefix, suffix = expected_parts

                # See if actual_line has the same structure
                if actual_line.startswith(prefix) and actual_line.endswith(suffix):
                    actual_value = actual_line[len(prefix):-len(suffix) if suffix else len(actual_line)]

                    # Try to figure out what template variable would produce this
                    if expression == "project_name" and actual_value != expected_value:
                        # Replace the variable with the new value
                        new_template_line = new_template_line.replace(pattern, actual_value)
                    elif expression == "project_title" and actual_value != expected_value:
                        new_template_line = new_template_line.replace(pattern, actual_value)
                    elif "project_name_snake" in expression and actual_value != expected_value:
                        # For snake case, see if it's a simple transformation
                        if actual_value == actual_value.replace('-', '_'):
                            new_template_line = new_template_line.replace(pattern, actual_value)

    # Only return if we actually changed something
    return new_template_line if new_template_line != template_line else None


def attempt_jinja_auto_resolution(
    template_file: Path,
    expected_content: str,
    actual_content: str
) -> Optional[str]:
    """Try to automatically resolve jinja template differences.

    Returns updated template content if successful, None if too complex.
    """
    if not template_file.exists():
        return None

    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            template_content = f.read()
    except (UnicodeDecodeError, PermissionError):
        return None

    template_lines = template_content.splitlines()
    expected_lines = expected_content.splitlines()
    actual_lines = actual_content.splitlines()

    # Get template variables
    variables = parse_template_variables()

    # Track changes made
    changes_made = False
    new_template_lines = template_lines.copy()

    # Compare line by line
    max_lines = max(len(expected_lines), len(actual_lines), len(template_lines))

    for i in range(max_lines):
        expected_line = expected_lines[i] if i < len(expected_lines) else ""
        actual_line = actual_lines[i] if i < len(actual_lines) else ""
        template_line = template_lines[i] if i < len(template_lines) else ""

        if expected_line != actual_line and template_line:
            resolved_line = attempt_simple_line_resolution(
                template_line, expected_line, actual_line, variables
            )

            if resolved_line:
                new_template_lines[i] = resolved_line
                changes_made = True

    if changes_made:
        return '\n'.join(new_template_lines)

    return None


def validate_auto_resolved_template(
    script_dir: Path,
    template_file: Path, 
    resolved_content: str,
    expected_materialized_content: str
) -> bool:
    """Validate that auto-resolved template produces expected output.
    
    Returns True if validation passes, False otherwise.
    """
    # Save current template content
    original_content = None
    if template_file.exists():
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except (UnicodeDecodeError, PermissionError):
            return False
    
    try:
        # Write resolved content temporarily
        template_file.parent.mkdir(parents=True, exist_ok=True)
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write(resolved_content)
        
        # Test regeneration in a temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            test_proj = Path(temp_dir) / "validation-proj"
            
            copier.run_copy(
                src_path=str(script_dir),
                dst_path=str(test_proj),
                data={"project_name": "test-proj", "project_title": "Test Project"},
                unsafe=True,
            )
            
            # Get the materialized file path
            relative_template_path = template_file.relative_to(script_dir)
            if relative_template_path.name.endswith('.jinja'):
                # Remove .jinja extension and handle template path mapping
                materialized_path_str = str(relative_template_path)[:-6]  # Remove .jinja
                # Handle {{ project_name_snake }} mapping
                if "{{ project_name_snake }}" in materialized_path_str:
                    materialized_path_str = materialized_path_str.replace("{{ project_name_snake }}", "test_proj")
                materialized_file = test_proj / materialized_path_str
            else:
                materialized_file = test_proj / relative_template_path
            
            if not materialized_file.exists():
                return False
            
            # Compare content
            try:
                with open(materialized_file, 'r', encoding='utf-8') as f:
                    actual_content = f.read()
                return actual_content.strip() == expected_materialized_content.strip()
            except (UnicodeDecodeError, PermissionError):
                return False
                
    except Exception:
        return False
    finally:
        # Restore original content if it existed
        if original_content is not None:
            try:
                with open(template_file, 'w', encoding='utf-8') as f:
                    f.write(original_content)
            except (UnicodeDecodeError, PermissionError):
                pass


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

                # Read file contents for auto-resolution
                try:
                    with open(expected_file, "r", encoding="utf-8") as f:
                        expected_content = f.read()
                    with open(actual_file, "r", encoding="utf-8") as f:
                        actual_content = f.read()
                except (UnicodeDecodeError, PermissionError):
                    expected_content = None
                    actual_content = None

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
                    # Try auto-resolution first
                    auto_resolved_content = None
                    if expected_content and actual_content:
                        auto_resolved_content = attempt_jinja_auto_resolution(
                            template_file, expected_content, actual_content
                        )
                    
                    if auto_resolved_content:
                        # Validate the auto-resolution before accepting it
                        if validate_auto_resolved_template(
                            script_dir, template_file, auto_resolved_content, actual_content
                        ):
                            click.echo(f"  ✓ Auto-resolved: {template_file_path}")
                            files_to_copy.append(
                                (str(file_path), template_file_path, None, template_file, auto_resolved_content)
                            )
                        else:
                            click.echo(f"  ⚠️ Auto-resolution failed validation: {template_file_path}")
                            files_needing_manual_fix.append((file_path, template_file_path))
                    else:
                        files_needing_manual_fix.append((file_path, template_file_path))
                else:
                    files_to_copy.append(
                        (str(file_path), template_file_path, actual_file, template_file, None)
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
                    # For extra files, we can't auto-resolve without expected content
                    files_needing_manual_fix.append((file_path, template_file_path))
                else:
                    files_to_copy.append(
                        (str(file_path), template_file_path, actual_file, template_file, None)
                    )

        # Provide guidance and optionally fix
        if not check_mode:
            click.echo("\nTo fix template files, you can:")
            click.echo("1. Copy non-templated files: run fix_template --fix")
            click.echo(
                "2. Manually update .jinja files based on the differences shown above"
            )
        else:
            if files_to_copy:
                click.echo(
                    f"\nCopying {len(files_to_copy)} files back to template:"
                )
                for (
                    relative_path,
                    template_path,
                    actual_file,
                    template_file,
                    auto_resolved_content,
                ) in files_to_copy:
                    click.echo(f"Copying {relative_path} → {template_path}")
                    template_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    if auto_resolved_content:
                        # Write auto-resolved jinja content
                        with open(template_file, 'w', encoding='utf-8') as f:
                            f.write(auto_resolved_content)
                    else:
                        # Copy regular file
                        shutil.copy2(actual_file, template_file)

            if files_needing_manual_fix:
                click.echo(
                    f"\n⚠️  {len(files_needing_manual_fix)} templated files need manual resolution:"
                )
                for materialized_path, template_path in files_needing_manual_fix:
                    click.echo(f"  {materialized_path} → {template_path}")





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
@click.option(
    "--check",
    is_flag=True,
    help="Show differences without making changes.",
)
def fix_template(check: bool) -> None:
    """Fix template files by copying back changes from materialized test-proj.

    Compares test-proj with what the current template would generate and fixes differences.
    Use --check to preview changes without applying them.
    """
    script_dir: Path = get_script_dir_and_setup()

    # Check if test-proj exists
    ensure_test_proj_exists(script_dir)

    # Use expected materialized comparison approach
    compare_with_expected_materialized(script_dir, check_mode=check)


if __name__ == "__main__":
    cli()
