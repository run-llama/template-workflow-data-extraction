#!/usr/bin/env -S uv run --script
# /// script
# dependencies=[
#     "copier",
#     "click",
#     "pyyaml",
#     "rich",
# ]
# ///

import warnings

# Suppress deprecation warnings from copier
warnings.filterwarnings("ignore", category=DeprecationWarning)

import os
import re
import shutil
import subprocess
import sys
import tempfile

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
import yaml
from rich.console import Console
from rich.spinner import Spinner

import copier
from copier._template import Template
from copier.errors import DirtyLocalWarning

warnings.filterwarnings("ignore", category=DirtyLocalWarning)

console = Console()


def run_copier_quietly(src_path: str, dst_path: str, data: Dict[str, str]) -> None:
    """Run copier with minimal output."""
    copier.run_copy(
        src_path=src_path,
        dst_path=dst_path,
        data=data,
        unsafe=True,
        quiet=True,
    )


def render_jinja_string(
    template_string: str, variables: Dict[str, str], script_dir: Path
) -> str:
    """Render a Jinja template string using Copier's configuration."""
    template = Template(url=str(script_dir))

    import jinja2

    jinja_env = jinja2.Environment(
        loader=jinja2.BaseLoader(),
        extensions=template.jinja_extensions,
        **template.envops,
    )

    return jinja_env.from_string(template_string).render(**variables)


def parse_template_variables() -> Dict[str, str]:
    """Parse template variables using Copier's Jinja environment."""
    script_dir = Path(__file__).parent.parent

    # Read answers from existing materialized project
    test_proj = script_dir / "test-proj"
    answers_file = test_proj / ".copier-answers.yml"

    with open(answers_file, "r") as f:
        answers_data = yaml.safe_load(f)
        # Filter out copier metadata
        user_answers = {k: v for k, v in answers_data.items() if not k.startswith("_")}

    # Get template configuration for variable parsing
    template = Template(url=str(script_dir))

    # Build complete variable context by evaluating template defaults
    result = dict(user_answers)

    # Multiple passes to handle dependencies between computed variables
    max_iterations = 10
    for iteration in range(max_iterations):
        changed = False
        for question_name, question_config in template.questions_data.items():
            if question_name not in result and "default" in question_config:
                default_value = question_config["default"]
                if isinstance(default_value, str) and "{{" in default_value:
                    # Evaluate Jinja expression using our helper
                    try:
                        rendered = render_jinja_string(
                            default_value, result, script_dir
                        )
                        result[question_name] = rendered
                        changed = True
                    except Exception as e:
                        # Skip variables that can't be evaluated yet
                        pass
                else:
                    result[question_name] = default_value
                    changed = True

        # Stop if no new variables were computed
        if not changed:
            break
    return result


def find_simple_jinja_patterns(template_line: str) -> List[Tuple[str, str]]:
    """Find simple jinja variable patterns in a template line.

    Returns list of (pattern, variable_name) tuples.
    """
    patterns = []

    # Find {{variable}} patterns
    variable_pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}"
    for match in re.finditer(variable_pattern, template_line):
        patterns.append((match.group(0), match.group(1)))

    # Find {{variable.method()}} patterns (simple transforms)
    transform_pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_().\-\'" ]+)\s*\}\}'
    for match in re.finditer(transform_pattern, template_line):
        patterns.append((match.group(0), match.group(1)))

    return patterns


def evaluate_jinja_expression(
    expression: str, variables: Dict[str, str]
) -> Optional[str]:
    """Safely evaluate simple jinja expressions."""
    try:
        # Handle simple variable references
        if expression in variables:
            return variables[expression]

        # Handle simple method calls on variables
        if "." in expression:
            var_name = expression.split(".")[0]
            if var_name in variables:
                value = variables[var_name]

                # Handle common string methods
                if ".replace('-', '_')" in expression:
                    return value.replace("-", "_")
                elif ".replace('-', ' ').title()" in expression:
                    return value.replace("-", " ").title()
                elif ".replace('_', '-')" in expression:
                    return value.replace("_", "-")

        return None
    except Exception:
        return None


def attempt_simple_line_resolution(
    template_line: str, expected_line: str, actual_line: str, variables: Dict[str, str]
) -> Optional[str]:
    """Try to resolve a single line difference by updating jinja template.

    Returns updated template line if successful, None if too complex.
    """
    # Skip if template line has no jinja patterns
    jinja_patterns = find_simple_jinja_patterns(template_line)
    if not jinja_patterns:
        return None

    # Skip complex jinja (conditionals, loops, etc.)
    if "{%" in template_line or "{#" in template_line:
        return None

    # Simple approach: for lines with variables, update the literal parts
    # Validation will ensure this actually works
    if len(jinja_patterns) == 1:
        pattern, var_name = jinja_patterns[0]
        var_value = variables.get(var_name, "")

        # If both lines contain the variable value, update surrounding text
        if var_value and var_value in expected_line and var_value in actual_line:
            expected_parts = expected_line.split(var_value)
            actual_parts = actual_line.split(var_value)

            if len(expected_parts) == 2 and len(actual_parts) == 2:
                # Replace literal text around the variable
                actual_prefix, actual_suffix = actual_parts
                result = f"{actual_prefix}{pattern}{actual_suffix}"
                return result

    return None


def attempt_jinja_auto_resolution(
    template_file: Path, expected_content: str, actual_content: str, variables: Dict[str, str]
) -> Optional[str]:
    """Try to automatically resolve jinja template differences.

    Returns updated template content if successful, None if too complex.
    """
    if not template_file.exists():
        return None

    with open(template_file, "r", encoding="utf-8") as f:
        template_content = f.read()

    template_lines = template_content.splitlines()
    expected_lines = expected_content.splitlines()
    actual_lines = actual_content.splitlines()

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
        proposed_content = "\n".join(new_template_lines)

        # Validate the proposed fix before accepting it
        script_dir = Path(__file__).parent.parent
        if validate_auto_resolved_template(
            script_dir, template_file, proposed_content, actual_content
        ):
            return proposed_content

    return None


def validate_auto_resolved_template(
    script_dir: Path,
    template_file: Path,
    resolved_content: str,
    expected_materialized_content: str,
) -> bool:
    """Validate that auto-resolved template produces expected output.

    Returns True if validation passes, False otherwise.
    """
    # Save current template content
    original_content = None
    if template_file.exists():
        with open(template_file, "r", encoding="utf-8") as f:
            original_content = f.read()

    try:
        # Write resolved content temporarily
        template_file.parent.mkdir(parents=True, exist_ok=True)
        with open(template_file, "w", encoding="utf-8") as f:
            f.write(resolved_content)

        # Test regeneration in a temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            test_proj = Path(temp_dir) / "validation-proj"

            run_copier_quietly(
                str(script_dir),
                str(test_proj),
                parse_template_variables(),
            )

            # Get the materialized file path using existing template mapping logic
            relative_template_path = template_file.relative_to(script_dir)

            # Use the reverse of map_materialized_to_template_path to get materialized path
            if relative_template_path.name.endswith(".jinja"):
                materialized_path_str = str(relative_template_path).removesuffix(
                    ".jinja"
                )
            else:
                materialized_path_str = str(relative_template_path)

            # Apply template variable substitution to the path
            variables = parse_template_variables()
            materialized_path_str = render_jinja_string(
                materialized_path_str, variables, script_dir
            )

            materialized_file = test_proj / materialized_path_str

            if not materialized_file.exists():
                return False

            # Compare content
            with open(materialized_file, "r", encoding="utf-8") as f:
                validation_actual = f.read()

            expected_stripped = expected_materialized_content.strip()
            actual_stripped = validation_actual.strip()

            return actual_stripped == expected_stripped

    except Exception:
        return False
    finally:
        # Restore original content if it existed
        if original_content:
            with open(template_file, "w", encoding="utf-8") as f:
                f.write(original_content)


def run_git_command(
    cmd: List[str], cwd: Optional[Path] = None
) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the result."""
    console.print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=True
        )
        return result
    except subprocess.CalledProcessError as e:
        console.print(f"Command failed with exit code {e.returncode}", style="bold red")
        console.print(f"stdout: {e.stdout}", style="bold yellow")
        console.print(f"stderr: {e.stderr}", style="bold yellow")
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

    # Use git ls-files to get files that git would track
    # This respects .gitignore rules
    result = subprocess.run(
        ["git", "ls-files", "--others", "--cached", "--exclude-standard"],
        cwd=directory,
        capture_output=True,
        text=True,
        check=True,
    )

    tracked_files = set()
    for line in result.stdout.strip().split("\n"):
        if line.strip():
            file_path = directory / line.strip()
            relative_path = Path(line.strip())
            if file_path.is_file() and relative_path.name not in ignored_files:
                tracked_files.add(relative_path)

    return tracked_files


def compare_directories(expected_dir: Path, actual_dir: Path) -> List[str]:
    """Compare two directories and return list of files that differ, respecting gitignore."""
    differences = []

    # Get files in both directories
    # For expected (temp) directory: get all files (no gitignore)
    # For actual directory: respect gitignore
    expected_files = (
        get_git_tracked_files(expected_dir, respect_gitignore=False)
        if expected_dir.exists()
        else set()
    )
    actual_files = (
        get_git_tracked_files(actual_dir, respect_gitignore=True)
        if actual_dir.exists()
        else set()
    )

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

        with open(expected_file, "r", encoding="utf-8") as f:
            expected_content = f.read()
        with open(actual_file, "r", encoding="utf-8") as f:
            actual_content = f.read()

        if expected_content != actual_content:
            differences.append(f"Content differs: {file_path}")

    return differences


def compare_with_expected_materialized(
    script_dir: Path, fix_mode: bool = False
) -> None:
    """Compare current test-proj with freshly generated template."""

    with console.status(
        "[bold green]Generating expected materialized version from current template..."
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            expected_proj = Path(temp_dir) / "expected-proj"

            # Generate expected materialized version
            run_copier_quietly(
                str(script_dir),
                str(expected_proj),
                parse_template_variables(),
            )

            # Compare expected vs actual
            test_proj_dir = script_dir / "test-proj"
            differences = compare_directories(expected_proj, test_proj_dir)

            if not differences:
                console.print(
                    "✅ test-proj matches expected template output", style="bold green"
                )
                return

            console.print(
                f"\n❌ Found {len(differences)} differences between expected and actual:",
                style="bold red",
            )
            for diff in differences:
                console.print(f"  {diff}")

            files_to_copy = []
            files_needing_manual_fix = []
            
            # Parse template variables once for auto-resolution
            variables = parse_template_variables()

            # For files that differ in content, show detailed diff and categorize
            console.print("\nDetailed differences:")
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

                    console.print(f"\n--- Expected (from template): {file_path}")
                    console.print(f"+++ Actual (in test-proj): {file_path}")

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
                                    console.print(f"  {line}")
                    except subprocess.CalledProcessError:
                        # Fallback to basic diff indication
                        console.print("  (Files differ)")

                    # Categorize for fixing
                    if template_file_path.endswith(".jinja"):
                        # Try auto-resolution first
                        auto_resolved_content = None
                        if expected_content and actual_content:
                            auto_resolved_content = attempt_jinja_auto_resolution(
                                template_file, expected_content, actual_content, variables
                            )

                        if auto_resolved_content:
                            # Accept the auto-resolution (our logic is conservative enough)
                            if fix_mode:
                                console.print(
                                    f"  ✓ Auto-resolved: {template_file_path}"
                                )
                            else:
                                console.print(
                                    f"  ✓ Would auto-resolve: {template_file_path}"
                                )
                            files_to_copy.append(
                                (
                                    str(file_path),
                                    template_file_path,
                                    None,
                                    template_file,
                                    auto_resolved_content,
                                )
                            )
                        else:
                            files_needing_manual_fix.append(
                                (file_path, template_file_path)
                            )
                    else:
                        files_to_copy.append(
                            (
                                str(file_path),
                                template_file_path,
                                actual_file,
                                template_file,
                                None,
                            )
                        )

                elif diff.startswith("Extra file: "):
                    file_path = diff[len("Extra file: ") :]
                    actual_file = test_proj_dir / file_path

                    # Determine corresponding template file path
                    template_file_path = map_materialized_to_template_path(
                        script_dir, str(file_path)
                    )
                    template_file = script_dir / template_file_path

                    console.print(f"\nExtra file in test-proj: {file_path}")

                    # Categorize for fixing
                    if template_file_path.endswith(".jinja"):
                        # For extra files, we can't auto-resolve without expected content
                        files_needing_manual_fix.append((file_path, template_file_path))
                    else:
                        files_to_copy.append(
                            (
                                str(file_path),
                                template_file_path,
                                actual_file,
                                template_file,
                                None,
                            )
                        )

    # Provide guidance and optionally fix (outside temp directory)
    if fix_mode:
        # Actually fix the files
        if files_to_copy:
            console.print(f"\nCopying {len(files_to_copy)} files back to template:")
            for (
                relative_path,
                template_path,
                actual_file,
                template_file,
                auto_resolved_content,
            ) in files_to_copy:
                console.print(f"Copying {relative_path} → {template_path}")
                template_file.parent.mkdir(parents=True, exist_ok=True)

                if auto_resolved_content:
                    # Write auto-resolved jinja content
                    with open(template_file, "w", encoding="utf-8") as f:
                        f.write(auto_resolved_content)
                else:
                    # Copy regular file
                    shutil.copy2(actual_file, template_file)

        if files_needing_manual_fix:
            console.print(
                f"\n⚠️  {len(files_needing_manual_fix)} templated files need manual resolution:"
            )
            for materialized_path, template_path in files_needing_manual_fix:
                console.print(f"  {materialized_path} → {template_path}")
    else:
        # In check mode, just show what would happen
        if files_to_copy or files_needing_manual_fix:
            console.print("\nWould make the following changes:")
            if files_to_copy:
                console.print(f"  Copy {len(files_to_copy)} files back to template")
            if files_needing_manual_fix:
                console.print(
                    f"  {len(files_needing_manual_fix)} files need manual resolution"
                )
            console.print("\nTo apply changes, run: fix-template")


def map_materialized_to_template_path(script_dir: Path, materialized_path: str) -> str:
    """Map a materialized file path back to its template path."""
    path_parts: tuple[str, ...] = Path(materialized_path).parts

    # Handle the special case of src/{computed_name}/ → src/{{ project_name_snake }}/
    variables = parse_template_variables()
    project_name_snake = variables.get("project_name_snake", "test_proj")
    if (
        len(path_parts) >= 2
        and path_parts[0] == "src"
        and path_parts[1] == project_name_snake
    ):
        # Replace computed name with the template variable
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
    test_proj_dir: Path = script_dir / "test-proj"
    
    # Parse template variables before deleting the directory
    variables = parse_template_variables() if test_proj_dir.exists() else {}
    
    # Delete the test-proj directory if it exists
    if test_proj_dir.exists():
        console.print(f"Deleting {test_proj_dir}")
        shutil.rmtree(test_proj_dir)
    else:
        console.print(f"Directory {test_proj_dir} does not exist")

    # Run copier to regenerate test-proj
    with console.status("[bold green]Running copier to regenerate test-proj..."):
        run_copier_quietly(
            str(script_dir),
            str(test_proj_dir),
            variables,
        )
    
    # Revert the .copier-answers.yml file since it gets updated with new revision info
    answers_file = test_proj_dir / ".copier-answers.yml"
    if answers_file.exists():
        try:
            run_git_command(["git", "restore", str(answers_file)], cwd=script_dir)
        except SystemExit:
            # If git restore fails (e.g., file not tracked), just continue
            pass


def get_script_dir_and_setup() -> Path:
    """Get the script directory and set up working directory. Common setup for all commands."""
    script_dir: Path = Path(__file__).parent.parent
    os.chdir(script_dir)
    console.print(f"Working directory: {script_dir}")
    return script_dir


def ensure_test_proj_exists(script_dir: Path) -> Path:
    """Ensure test-proj directory exists and return its path."""
    test_proj_dir: Path = script_dir / "test-proj"
    if not test_proj_dir.exists():
        console.print(
            "Error: test-proj directory does not exist. Run 'regenerate' first.",
            style="bold red",
        )
        sys.exit(1)
    return test_proj_dir


@cli.command()
def regenerate() -> None:
    """Regenerate test-proj directory using copier."""
    script_dir: Path = get_script_dir_and_setup()

    # Check for uncommitted changes before starting
    console.print("Checking for uncommitted changes...")
    git_status_check: subprocess.CompletedProcess[str] = run_git_command(
        ["git", "status", "--porcelain"], cwd=script_dir
    )
    if git_status_check.stdout.strip():
        console.print(
            "Error: Repository has uncommitted changes. Please commit or stash them first.",
            style="bold red",
        )
        console.print(git_status_check.stdout)
        sys.exit(1)

    regenerate_test_proj(script_dir)
    console.print("✓ test-proj regenerated")


@cli.command()
def check_regeneration() -> None:
    """Check if generated files match template (assumes test-proj already exists)."""
    script_dir: Path = get_script_dir_and_setup()

    regenerate_test_proj(script_dir)

    # Check if generated files match template
    console.print("Checking generated files against template...")
    git_status: subprocess.CompletedProcess[str] = run_git_command(
        ["git", "status", "--porcelain"], cwd=script_dir
    )

    if git_status.stdout.strip():
        console.print("\n❌ Generated files do not match template!", style="bold red")
        console.print("\nFiles that differ:")
        console.print(git_status.stdout)

        console.print("\nDifferences:")
        git_diff: subprocess.CompletedProcess[str] = run_git_command(
            ["git", "diff"], cwd=script_dir
        )
        console.print(git_diff.stdout)

        console.print(
            "\nTo fix: If these changes look good, likely you just need to run regenerate and commit the changes.",
            style="bold red",
        )
        sys.exit(1)
    else:
        console.print("✓ Generated files match template")


def run_python_checks(test_proj_dir: Path, fix: bool) -> None:
    """Run Python validation checks on test-proj using hatch."""
    # Run Python checks with hatch
    console.print("Running Python validation checks...")
    run_git_command(
        ["uv", "run", "hatch", "run", "all-fix" if fix else "all-check"],
        cwd=test_proj_dir,
    )
    console.print("✓ Python checks passed")


@cli.command("check-python")
@click.option("--fix", is_flag=True, help="Fix formatting issues automatically.")
def check_python(fix: bool) -> None:
    """Run Python validation checks on test-proj using hatch."""
    script_dir: Path = get_script_dir_and_setup()
    test_proj_dir: Path = ensure_test_proj_exists(script_dir)
    run_python_checks(test_proj_dir, fix)


def run_javascript_checks(test_proj_dir: Path, fix: bool) -> None:
    """Run TypeScript and format validation checks on test-proj/ui using npm."""
    ui_dir: Path = test_proj_dir / "ui"

    # Check if ui directory exists
    if not ui_dir.exists():
        console.print("Error: test-proj/ui directory does not exist.", style="bold red")
        sys.exit(1)

    # Run TypeScript checks with npm
    console.print("Running TypeScript validation checks...")
    run_git_command(["npm", "run", "all-fix" if fix else "all-check"], cwd=ui_dir)
    console.print("✓ TypeScript checks passed")


@cli.command("check-javascript")
@click.option("--fix", is_flag=True, help="Fix formatting issues automatically.")
def check_javascript(fix: bool) -> None:
    """Run TypeScript and format validation checks on test-proj/ui using npm."""
    script_dir: Path = get_script_dir_and_setup()
    test_proj_dir: Path = ensure_test_proj_exists(script_dir)
    run_javascript_checks(test_proj_dir, fix)


@cli.command()
@click.option(
    "--fix",
    is_flag=True,
    help="Fix template files by copying back changes from materialized test-proj.",
)
@click.option(
    "--fix-format",
    is_flag=True,
    help="Run Python and JavaScript formatters before fixing template files. Implies --fix.",
)
def check_template(fix: bool, fix_format: bool) -> None:
    """Fix template files by copying back changes from materialized test-proj.

    Compares test-proj with what the current template would generate and fixes differences.
    Use --check to preview changes without applying them.
    """
    script_dir: Path = get_script_dir_and_setup()

    # Validate options
    if fix_format:
        # implies fix
        fix = True

    # Check if test-proj exists
    test_proj_dir: Path = ensure_test_proj_exists(script_dir)

    # Run formatters if requested
    if fix_format:
        run_python_checks(test_proj_dir, fix=True)
        run_javascript_checks(test_proj_dir, fix=True)

    # Use expected materialized comparison approach
    compare_with_expected_materialized(script_dir, fix_mode=fix)


if __name__ == "__main__":
    cli()
