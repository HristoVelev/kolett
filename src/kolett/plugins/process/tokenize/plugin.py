import logging
from typing import Any, Dict, Tuple

from kolett.plugins.base import ProcessPlugin

logger = logging.getLogger("kolett.plugins.process.tokenize")


class Plugin(ProcessPlugin):
    """
    Tokenize Process Plugin for Kolett.

    This plugin splits a string (usually a file path) by a delimiter and extracts
    specific tokens into the shared metadata context. This allows downstream
    plugins (like Copy or Retemplate) to use these names in their Jinja2 templates.
    """

    def run(
        self, source: str, destination: str, metadata: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Tokenizes the input string and adds found tokens to the metadata dictionary.

        Config options in settings.yaml:
            source_key: The metadata key to tokenize. If not found, defaults to the 'source' path.
            delimiter: The string to split by (e.g., "/", "_", "."). Default is "/".
            tokens: A dictionary mapping metadata keys to list indices.
        """
        source_key = self.config.get("source_key")
        delimiter = self.config.get("delimiter", "/")
        token_map = self.config.get("tokens", {})

        # 1. Determine input string (Metadata override -> Source path)
        input_string = None
        if source_key:
            input_string = metadata.get(source_key)

        if not input_string:
            input_string = source

        if not input_string:
            return True, destination

        # 2. Tokenize
        try:
            parts = input_string.split(delimiter)

            # 3. Extract and inject into metadata
            for name, index in token_map.items():
                try:
                    idx = int(index)
                    # Check bounds (supports negative indexing)
                    if idx < len(parts) and (idx >= 0 or abs(idx) <= len(parts)):
                        value = parts[idx]
                        metadata[name] = value
                        if self.dry_run:
                            logger.info(
                                f"DRY RUN: Tokenized '{name}' = '{value}' from index {idx}"
                            )
                    else:
                        logger.warning(
                            f"Tokenize: Index {idx} out of range for input '{input_string}'"
                        )
                except (ValueError, TypeError):
                    logger.error(
                        f"Tokenize: Invalid index '{index}' for token name '{name}'"
                    )

            return True, destination

        except Exception as e:
            logger.error(f"Tokenize plugin execution failed: {str(e)}")
            # We return True to not block the pipeline, but the tokens will be missing
            return True, destination
