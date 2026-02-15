from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple

from kolett.protocol import DeliveryOutput


class CallbackPlugin(ABC):
    """
    Base class for all Kolett callback plugins.
    Each plugin should be placed in its own directory under plugins/output/.
    """

    def __init__(self, config: Dict[str, Any], dry_run: bool = False):
        """
        Initializes the plugin with a specific configuration block
        defined in the engine config YAML.
        """
        self.config = config
        self.dry_run = dry_run

    @abstractmethod
    def run(self, delivery_output: DeliveryOutput) -> bool:
        """
        The main entry point for the plugin.
        Receives the result of the delivery and performs an action
        (e.g., notification, database update).

        Returns:
            bool: True if the plugin executed successfully, False otherwise.
        """
        pass


class ProcessPlugin(ABC):
    """
    Base class for all Kolett process plugins (copy, move, transcode, etc.).
    Each plugin should be placed in its own directory under plugins/process/.
    """

    def __init__(self, config: Dict[str, Any], dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run

    @abstractmethod
    def run(
        self, source: str, destination: str, metadata: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        The main entry point for the processing logic.

        Args:
            source: Path to the source file.
            destination: Initial target path for the file.
            metadata: Metadata available for this specific file.

        Returns:
            Tuple[bool, str]: (Success status, Actual final destination path)
        """
        pass
