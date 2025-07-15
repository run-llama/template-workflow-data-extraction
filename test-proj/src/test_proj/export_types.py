"""
Script to export pydantic types from a python file, defaulting to "schemas.py" to a json schema and then to a zod schema.

For sharing types precisely between python and typescript
"""

import importlib.util
import inspect
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

import jsonref
from pydantic import BaseModel
import click


def run_command(cmd: str):
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Command failed: {cmd}", file=sys.stderr)
        sys.exit(result.returncode)


@click.command()
@click.option(
    "--schema-file",
    default="schemas.py",
    help="The name of the model file to export types from"
)
def export_types(schema_file: str):
    app_path = Path(__file__).parent.parent.parent
    print("Exporting types...")
    schema_path = Path(__file__).parent / schema_file
    if not schema_path.exists():
        raise click.BadParameter(f"Schema file '{schema_file}' not found in app")
    print(f"Exporting types from {schema_path}...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "types"
        ts_output_dir = app_path / "ui" / "src" / "schemas"
        export_schemas(schema_path, output_dir)
        schema_dir_to_zod_schema(output_dir, ts_output_dir)


def schema_dir_to_zod_schema(schema_dir: Path, output_dir: Path):
    if output_dir.exists():
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    for file in schema_dir.glob("*.json"):
        name = file.name.replace(".json", "")
        run_command(
            f"npx -y json-schema-to-zod@2.6.1 --name {name} --module esm --type {name} -i {file} -o {output_dir / file.name.replace('.json', '.ts')}"
        )
    # Replace zod import in generated files to use v4
    for ts_file in output_dir.glob("*.ts"):
        with open(ts_file, "r") as f:
            content = f.read()
        content = content.replace(
            'import { z } from "zod"', 'import { z } from "zod/v4"'
        )
        with open(ts_file, "w") as f:
            f.write(content)
    run_command(f"npx -y prettier@3.5.1 --write {output_dir}")


def load_module_from_path(module_name: str, file_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, file_path)
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
