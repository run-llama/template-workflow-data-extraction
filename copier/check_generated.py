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
            cmd, 
            cwd=cwd, 
            capture_output=True, 
            text=True, 
            check=True
        )
        return result
    except subprocess.CalledProcessError as e:
        click.echo(f"Command failed with exit code {e.returncode}", err=True)
        click.echo(f"stdout: {e.stdout}", err=True)
        click.echo(f"stderr: {e.stderr}", err=True)
        sys.exit(1)


@click.command()
def main():
    """Regenerate test-proj directory using copier and show git changes."""
    # Get the parent directory of this script (go up from copier/ to project root)
    script_dir = Path(__file__).parent.parent
    os.chdir(script_dir)
    
    click.echo(f"Working directory: {script_dir}")
    
    # Check for uncommitted changes before starting
    click.echo("Checking for uncommitted changes...")
    git_status_check = run_git_command(["git", "status", "--porcelain"], cwd=script_dir)
    if git_status_check.stdout.strip():
        click.echo("Error: Repository has uncommitted changes. Please commit or stash them first.", err=True)
        click.echo(git_status_check.stdout)
        sys.exit(1)
    
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
        data={
            "project_name": "test-proj",
            "project_title": "Test Project"
        },
        unsafe=True
    )
    
    # Check if generated files match template
    click.echo("\nChecking generated files against template...")
    git_status = run_git_command(["git", "status", "--porcelain"], cwd=script_dir)
    
    if git_status.stdout.strip():
        click.echo("\n❌ Generated files do not match template!", err=True)
        click.echo("\nFiles that differ:")
        click.echo(git_status.stdout)
        
        click.echo("\nDifferences:")
        git_diff = run_git_command(["git", "diff"], cwd=script_dir)
        click.echo(git_diff.stdout)
        
        click.echo("\nTo fix: Update the template files to match the current test-proj output", err=True)
        sys.exit(1)
    else:
        click.echo("✓ Generated files match template")


if __name__ == "__main__":
    main()