# Data Extraction and Ingestion

This is a starter for a [`llama_deploy`](https://github.com/run-llama/llama_deploy) powered app.


## Installation and Local Development

`uv` is used for python, and `pnpm` for JavaScript. They both use workspaces to link packages in this monorepo

### Python Setup

First, [install `uv`](https://docs.astral.sh/uv/getting-started/installation/).

To set up a virtual environment with `uv`, run `uv sync`. You can either activate this single virtual environment, or just `uv run <cmd>` to run `<cmd>` within `uv`s venv.
`uv run` will roughly install the correct dependencies, and run it within the virtual environment. For example `uv run python my_workflow.py`

### JavaScript Setup

To set up `pnpm` run `corepack enable` in the `/ui` directory. `corepack` is a "package manager package manager" that is normally installed alongside Node.js. This project is using node v22.

Run `pnpm i` to install all dependencies.

### Environments and `.env`

There is a template `.env` file. Copy this file and edit its values: `cp .env.template .env` 
The backend python workflow and frontend ui share values from this single file.

### Serving locally with llamactl

These apps are built on top of `llama_deploy`, which comes bundled with a `llamactl` cli for serving your workflows as an API, and your app, side by side.

You can serve it locally with `uv run llamactl serve llama_deploy.local` from within this directory.

After starting with `llamactl`, visit `http://localhost:4501/deployments//ui` to see the UI.

## Exporting types

To generate typescript types for sharing with the UI from your `schema.py`, run `uv run export-types` from this directory. This will export json schemas and typescript
types to the ui under `ui/src/schemas` for every pydantic model in `schemas.py`. The UI uses the schemas in order to structure its UI, so make sure to run this after
you modify you pydantic schemas.

### Running Workflows

The core value of this template is good extraction. The main python code is in the `src` directory.

Workflows can be triggered from the UI using `useWorkflow` react hooks. You can also add a `if __name__ == "__main__":` handler to individual 
workflows to run and debug them directly. Eventually there will be support for auto-running workflows in the app.  The `process_file.py` has main
handler that will upload a `test.pdf` from your current working directory so you can test your extraction directly.

### Workflow Files

The template includes the following files that you may customize:

- `process_file.py` - this is a workflow triggered for an individual file, triggered from the UI.
- `config.py` - Environment and secret parsing, and basic client interface construction
- `schemas.py` - Write pydantic schemas here. Don't add additional dependencies to this file. `builder` can read this file and autogenerate zod schemas for the ui
- `.env` - Add environment variables here as needed for running locally, and parse them in the code
- `pyproject.toml` - Uses `uv` standards. Add dependencies here with `uv add <dependency>` for example `uv add cv2`
