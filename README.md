# Kolett 📦

**Kolett** (from the Bulgarian *kolet* for delivery) is an open-source, database-agnostic delivery tool designed for creative teams. It automates the process of fetching assets, retemplating them to client protocols, generating manifests, and notifying stakeholders.

## 🚀 The Philosophy: "Emancipated Database"

Kolett is built on an **Open Protocol** architecture. Unlike traditional pipeline tools that are tightly coupled to a specific database (like ShotGrid or Ftrack), Kolett doesn't care where your data lives.

1.  **Input Plugin (The Connector):** A script that fetches data from your source (Grist, ShotGrid, a CSV) and emits a standardized **Kolett Manifest JSON**.
2.  **Engine (Kolett Core):** A "dumb" worker that reads the JSON, performs file operations on shared storage, and renders a human-readable **Markdown Manifest**.
3.  **Output Plugin (The Callback):** Updates your database with the result of the delivery, notifies stakeholders, and generates a report.

## 🛠 Features

- **Jinja2 Templating:** Use powerful Jinja2 logic for both file renaming and manifest generation.
- **Markdown Manifests:** Automatically generates `.md` manifests that are easy to read in browsers, file explorers, and email notifications.
- **Storage Agnostic:** Works across local SSDs, NFS, and JuiceFS.
- **Notification Ready:** Designed to trigger Mattermost, Slack, or Email notifications upon completion.

## 📁 Directory Structure

- `src/kolett/`: The core Python engine.
- `templates/`: Jinja2 templates for Markdown manifests.
- `configs/`: YAML settings for your studio environment.
- `plugins/`: Connectors for various data sources (Grist, etc.).

## 🚥 Quick Start

### 1. Requirements
```bash
pip install -r requirements.txt
```

### 2. Run a Delivery
To run a delivery, you pass a JSON file following the Kolett Open Protocol:

```bash
python -m kolett.main path/to/input.json --config configs/settings.yaml
```

### 3. Example Input JSON (`input.json`)
```json
{
  "package_name": "BTL_EP01_20260215",
  "client_config": "netflix_spec_v2",
  "items": [
    {
      "source_path": "/mnt/prod/projects/projA/shots/s01/render/v004/image.exr",
      "target_template": "{{ shot_name }}_{{ version }}.{{ extension }}",
      "metadata": {
        "shot_name": "s01",
        "version": "v004",
        "extension": "exr"
      }
    }
  ]
}
```

## 🤝 Contributing

Kolett is designed to be extensible. We encourage the community to contribute:
- **Input Plugins:** Connectors for Airtable, ShotGrid, Kitsu, etc.
- **Notification Plugins:** Webhook handlers for various chat platforms.
- **Templates:** Client-standard manifest templates.

---
*Maintained by Hristo Velev and the BTL VFX Team.*
