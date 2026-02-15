from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PackageItem(BaseModel):
    """
    Represents a single item (shot, asset, etc.) within a delivery package.
    """

    source_path: str = Field(
        ..., description="Absolute path to the source file or sequence directory"
    )
    target_template: str = Field(
        ..., description="Jinja2 template for the target filename/path"
    )
    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Metadata used for template rendering"
    )


class DeliveryInput(BaseModel):
    """
    The standardized 'Open Protocol' JSON input for Kolett.
    This is what connectors (Grist, Shotgrid, etc.) should generate.
    """

    package_name: str = Field(..., description="Name of the delivery folder/package")
    client_config: str = Field(
        ..., description="Identifier for client-specific settings or templates"
    )
    items: List[PackageItem] = Field(..., description="List of items to be delivered")
    callbacks: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Callback plugins and their configurations"
    )
    notifications: List[str] = Field(
        default_factory=list,
        description="List of notification plugins to trigger (Legacy)",
    )
    destination_root: Optional[str] = Field(
        None, description="Override the default delivery root from config"
    )
    dry_run: bool = Field(
        False, description="If True, no files will be moved and no callbacks executed"
    )


class ItemResult(BaseModel):
    """
    Status of an individual item after processing.
    """

    source: str
    destination: str
    success: bool
    error: Optional[str] = None


class DeliveryOutput(BaseModel):
    """
    The standardized result JSON emitted by Kolett.
    This can be sent back to the database (Grist) to update statuses.
    """

    package_name: str
    delivery_path: str
    manifest_path: str
    timestamp: str
    results: List[ItemResult]
    summary: str
