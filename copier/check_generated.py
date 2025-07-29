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
from pathlib import Path
import click
import copier


def run_git_command(cmd, cwd=None):
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


def fix_template_from_materialized(script_dir, revision):
    """Fix template files by copying back files changed since revision from materialized test-proj."""
    test_proj_dir = script_dir / "test-proj"
    
    # Get list of files changed since the specified revision in test-proj
    git_diff_name_only = run_git_command([
        "git", "diff", "--name-only", revision, "--", "test-proj/"
    ], cwd=script_dir)
    
    if not git_diff_name_only.stdout.strip():
        click.echo(f"No changes in test-proj since {revision}")
        return
    
    changed_files = git_diff_name_only.stdout.strip().split("\n")
    
    for file_path in changed_files:
        # Remove test-proj/ prefix to get relative path within the project
        if not file_path.startswith("test-proj/"):
            continue
        
        relative_path = file_path[len("test-proj/"):]
        materialized_file = script_dir / file_path
        
        # Skip files that don't exist (deleted files)
        if not materialized_file.exists():
            click.echo(f"Skipping deleted file: {relative_path}")
            continue
        
        # Handle template path mapping
        template_file_path = map_materialized_to_template_path(script_dir, relative_path)
        template_file = script_dir / template_file_path
        
        if template_file_path.endswith(".jinja"):
            # Show warning for .jinja files that need manual resolution
            click.echo(f"⚠️  Manual resolution required: {template_file_path}")
            click.echo(f"   Materialized file: {relative_path}")
            
            # Show diff for just this file since the revision
            git_diff = run_git_command([
                "git", "diff", revision, "--", file_path
            ], cwd=script_dir)
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


def map_materialized_to_template_path(script_dir, materialized_path):
    """Map a materialized file path back to its template path."""
    path_parts = Path(materialized_path).parts

    # Handle the special case of src/test_proj/ → src/{{ project_name_snake }}/
    if len(path_parts) >= 2 and path_parts[0] == "src" and path_parts[1] == "test_proj":
        # Replace test_proj with the template variable
        new_parts = ("src", "{{ project_name_snake }}") + path_parts[2:]
        template_path = str(Path(*new_parts))

        # Check if a .jinja version exists
        jinja_path = template_path + ".jinja"
        if (script_dir / jinja_path).exists():
            return jinja_path
        return template_path

    # For other paths, check if .jinja version exists
    jinja_path = materialized_path + ".jinja"
    if (script_dir / jinja_path).exists():
        return jinja_path

    return materialized_path


@click.group()
def cli():
    """Template validation and fixing tools."""
    pass


def regenerate_test_proj(script_dir):
    """Regenerate the test-proj directory using copier."""
    # Delete the test-proj directory if it exists
    test_proj_dir = script_dir / "test-proj"
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


@cli.command()
def regenerate():
    """Regenerate test-proj directory using copier."""
    # Get the parent directory of this script (go up from copier/ to project root)
    script_dir = Path(__file__).parent.parent
    os.chdir(script_dir)

    click.echo(f"Working directory: {script_dir}")

    # Check for uncommitted changes before starting
    click.echo("Checking for uncommitted changes...")
    git_status_check = run_git_command(["git", "status", "--porcelain"], cwd=script_dir)
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
def check():
    """Check if generated files match template (assumes test-proj already exists)."""
    # Get the parent directory of this script (go up from copier/ to project root)
    script_dir = Path(__file__).parent.parent
    os.chdir(script_dir)

    click.echo(f"Working directory: {script_dir}")

    # Check if test-proj exists
    test_proj_dir = script_dir / "test-proj"
    if not test_proj_dir.exists():
        click.echo("Error: test-proj directory does not exist. Run 'regenerate' first.", err=True)
        sys.exit(1)

    # Check if generated files match template
    click.echo("Checking generated files against template...")
    git_status = run_git_command(["git", "status", "--porcelain"], cwd=script_dir)

    if git_status.stdout.strip():
        click.echo("\n❌ Generated files do not match template!", err=True)
        click.echo("\nFiles that differ:")
        click.echo(git_status.stdout)

        click.echo("\nDifferences:")
        git_diff = run_git_command(["git", "diff"], cwd=script_dir)
        click.echo(git_diff.stdout)

        click.echo(
            "\nTo fix: Update the template files to match the current test-proj output",
            err=True,
        )
        sys.exit(1)
    else:
        click.echo("✓ Generated files match template")


@cli.command()
@click.argument("revision")
def fix(revision):
    """Fix template files by copying back files changed since REVISION from materialized test-proj."""
    # Get the parent directory of this script (go up from copier/ to project root)
    script_dir = Path(__file__).parent.parent
    os.chdir(script_dir)

    click.echo(f"Working directory: {script_dir}")

    # Validate that the revision exists
    try:
        run_git_command(["git", "rev-parse", "--verify", revision], cwd=script_dir)
    except subprocess.CalledProcessError:
        click.echo(f"Error: Revision '{revision}' not found", err=True)
        sys.exit(1)

    # Check for uncommitted changes before starting
    click.echo("Checking for uncommitted changes...")
    git_status_check = run_git_command(["git", "status", "--porcelain"], cwd=script_dir)
    if git_status_check.stdout.strip():
        click.echo(
            "Error: Repository has uncommitted changes. Please commit or stash them first.",
            err=True,
        )
        click.echo(git_status_check.stdout)
        sys.exit(1)

    # Check if test-proj exists
    test_proj_dir = script_dir / "test-proj"
    if not test_proj_dir.exists():
        click.echo("Error: test-proj directory does not exist. Run 'regenerate' first.", err=True)
        sys.exit(1)

    # Fix template files based on changes since revision
    fix_template_from_materialized(script_dir, revision)


if __name__ == "__main__":
    cli()
