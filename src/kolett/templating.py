import os
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, Template


def get_jinja_env(template_dir: str) -> Environment:
    """
    Creates a Jinja2 environment with common VFX filters.
    """
    env = Environment(
        loader=FileSystemLoader(template_dir),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Add common filters for path manipulation in templates
    env.filters["basename"] = os.path.basename
    env.filters["dirname"] = os.path.dirname
    env.filters["splitext"] = lambda x: os.path.splitext(x)[0]
    env.filters["extension"] = lambda x: os.path.splitext(x)[1]

    return env


def render_path(template_str: str, metadata: Dict[str, Any]) -> str:
    """
    Renders a file path template using provided metadata.
    Example: "{shot}_{version}.exr" -> "sh010_v001.exr"
    """
    template = Template(template_str)
    return template.render(**metadata)


def render_manifest(
    template_name: str, template_dir: str, context: Dict[str, Any]
) -> str:
    """
    Renders the Markdown manifest using a Jinja2 template file.
    """
    env = get_jinja_env(template_dir)
    template = env.get_template(template_name)
    return template.render(**context)
