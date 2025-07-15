# Data Extraction and Ingestion

This is a starter for a [`llama_deploy`](https://github.com/run-llama/llama_deploy) powered app.
This app currently expects to be run within the [agent-apps](https://github.com/run-llama/agent-apps) mono repo, as it has workspace dependencies from there. See that readme for more context.


## Installation and Local Development

`uv` is used for python, and `pnpm` for JavaScript. They both use workspaces to link packages in this monorepo

### Python Setup

First, [install `uv`](https://docs.astral.sh/uv/getting-started/installation/).

To set up a virtual environment with `uv`, run `uv sync`. uv workspaces uses a single shared virtual environment across applications. You can sync the dependencies for any other app in the mono repo by navigating to its directory and syncing it. e.g. `cd /apps/receipt-example/workflow` and `uv sync`. You can either activate this single virtual environment, or just `uv run <cmd>` to run `<cmd>` within `uv`. `uv run` will install the correct dependencies, and run it within the virtual environment. For example `uv run python my_workflow.py`

### JavaScript Setup

To set up `pnpm` run `corepack enable` in this directory. `corepack` is a "package manager package manager" that should be installed alongside Node.js. This project is using node v22.

Run `pnpm i` to install all dependencies.

### Environments and `.env`

The `workflow` and `ui` directory both load environment variables from a `.env` file placed in each directory. At a baseline, you will need to define a `EXTRACTED_DATA_TOKEN`. For now, that should just be set to the project_name, e.g. `EXTRACTED_DATA_TOKEN=test-proj. This is also where you would set up llama cloud API keys, urls, and any other configuration.


### Serving locally with llamactl

These apps are built on top of llama_deploy, which comes bundled with a llamactl cli for serving your workflows as an API, and your app, side by side.

You can serve it locally with `uv run llamactl serve deployment.yaml` from within this directory.

Note that the UI depends on the extracted_data_api, and you will need to run that service as well. See [agent-apps](https://github.com/run-llama/agent-apps/blob/main/README.md#running-the-extracted-data-api-backend) for instructions.

After starting with `llamactl`, visit `http://localhost:4501/ui/` to see the UI.


## Exporting types

To generate typescript types for sharing with the UI from your `schema.py`, run `uv run build/export_types.py` from this directory.

### Running Workflows

The core value of these extraction apps is good extraction. All of the infrastructure here is to try to simplify the boilerplate and supporting infrastructure, but provide a flexible and powerful runtime so that developers can focus on building high quality extraction. Data extraction takes place in `workflow`. 

The `workflow` directory is just a python project, and much about the deployment and library structure is still evolving. The main expectation is that they will be deployed with LlamaIndex `Workflow`'s as entry points.

To run the primary workflow, usually you should run `uv run python loop_files.py`, which will pull files indefinitely.

The current conventions are as follows:

- `loop_files.py` is the main entry point. This workflow runs indefinitely, and regularly checks the data source for data. The template `loop_files.py` adds a `__main__` entrypoint to this file, so you can run this workflow locally. _Aside: in the long term, (hopefully) we can offload this onto the next evolution of platform pipelines. Those can be responsible for download the files, and notifying a workflow of new data to be processed_
- `process_file.py` - this is a workflow triggered for an individual file. Usually triggered by the `loop_files.py` workflow, but eventually we can add functionality such as uploading a file one-off file via the extraction component UI
- `config.py` - Environment and secret parsing, and basic client interface construction
- `schemas.py` - Write pydantic schemas here. Don't add additional dependencies to this file. `builder` can read this file and autogenerate zod schemas for the ui
- `.env` - Add environment variables here as needed for running locally, and parse them in the code
- `pyproject.toml` - Uses `uv` standards. Add dependencies here with `uv add <dependency>` for example `uv add cv2`
