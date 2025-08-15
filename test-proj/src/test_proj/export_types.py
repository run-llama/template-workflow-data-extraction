"""
Script to export pydantic types from a python file (default "schemas.py") to json schemas and then to typescript interfaces.

For sharing types precisely between python and typescript
"""

import importlib.util
import inspect
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import jsonref
from pydantic import BaseModel
import click
import re


def run_command(cmd: str):
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Command failed: {cmd}", file=sys.stderr)
        sys.exit(result.returncode)


@click.command()
@click.option(
    "--schema-file",
    default="schemas.py",
    help="The name of the model file to export types from",
)
def export_types(schema_file: str):
    app_path = Path(__file__).parent.parent.parent
    print("Exporting types...")
    schema_path = Path(__file__).parent / schema_file
    if not schema_path.exists():
        raise click.BadParameter(f"Schema file '{schema_file}' not found in app")
    print(f"Exporting types from {schema_path}...")
    output_dir = app_path / "ui" / "src" / "schemas"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    export_schemas(schema_path, output_dir)
    generate_typescript_interfaces(output_dir)


def generate_typescript_interfaces(schema_dir: Path):
    run_command(
        f"npx -y json-schema-to-typescript@15.0.4 -i '{schema_dir / '*.json'}' -o {schema_dir}"
    )
    post_process_typescript_declarations(schema_dir)
    run_command(f"npx -y prettier@3.5.1 --write {schema_dir}")


def post_process_typescript_declarations(schema_dir: Path) -> None:
    """Replace index signature value type with JSONObject and insert import.

    - Turns `[k: string]: unknown;` and `[k: string]: any;` into `[k: string]: JSONObject;`
    - Adds `import type { JSONObject } from '@llamaindex/ui';` if needed
    """
    index_signature_unknown_pattern = re.compile(r"\[k:\s*string\]:\s*unknown;?")
    index_signature_any_pattern = re.compile(r"\[k:\s*string\]:\s*any;?")
    import_statement = "import type { JSONObject } from '@llamaindex/ui';\n"
    import_regex = re.compile(r"import\s+type\s+\{\s*JSONObject\s*\}\s+from\s+'@llamaindex/ui';")

    for dts_path in schema_dir.glob("*.d.ts"):
        content = dts_path.read_text(encoding="utf-8")

        # Replace index signature value types
        new_content = index_signature_unknown_pattern.sub("[k: string]: JSONObject;", content)
        new_content = index_signature_any_pattern.sub("[k: string]: JSONObject;", new_content)

        # Insert import if JSONObject is used and import not present
        if "JSONObject" in new_content and not import_regex.search(new_content):
            # Try to place after the generator banner if present, else at file start
            insertion_index = 0
            banner_end = new_content.find("*/")
            if banner_end != -1:
                # Move to the next newline after banner
                next_newline = new_content.find("\n", banner_end + 2)
                insertion_index = next_newline + 1 if next_newline != -1 else banner_end + 2
            new_content = new_content[:insertion_index] + import_statement + new_content[insertion_index:]

        if new_content != content:
            dts_path.write_text(new_content, encoding="utf-8")


def load_module_from_path(module_name: str, file_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Failed to load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def export_schemas(py_file: Path, output_dir: Path):
    module_name = os.path.splitext(os.path.basename(py_file))[0]
    module = load_module_from_path(module_name, py_file)
    os.makedirs(output_dir, exist_ok=True)
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj is not BaseModel:
            schema = obj.model_json_schema()
            normalized_schema = jsonref.replace_refs(schema, proxies=False)
            with open(os.path.join(output_dir, f"{name}.json"), "w") as f:
                f.write(json.dumps(normalized_schema, indent=2))
            print(f"Exported {name} to {name}.json")


if __name__ == "__main__":
    export_types()
