
# KubeForge

KubeForge is an open-source CLI tool for managing Kubernetes clusters.

The project aims to support local, VPS, and AWS environments.

## Features

- Create local Kubernetes clusters using kind
- Configure cluster names and worker nodes
- Manage clusters with `up`, `status`, and `down`
- Load configuration from YAML
- Validate configuration using Pydantic
- Check system dependencies and resources
- Automated tests with GitHub Actions

## Requirements

- Linux
- Python 3.10+
- Docker
- kind
- kubectl

## Installation

```bash
git clone https://github.com/TinyKinder/KubeForge.git
cd KubeForge

python3 -m venv .venv
source .venv/bin/activate

pip install -e .
```

## Configuration

Create a `kubeforge.yaml` file:

```yaml
cluster:
  name: kubeforge
  provider: local
  workers: 2
```

## Usage

Check system requirements:

```bash
kubeforge doctor
```

Create a cluster:

```bash
kubeforge up
```

Check cluster status:

```bash
kubeforge status
```

Delete a cluster:

```bash
kubeforge down
```

## Project Status

Early development (v0.1.0).

Currently, only the local provider is implemented.
VPS and AWS support are planned.
