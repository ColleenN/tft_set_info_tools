"""Interface for locating/classifying a set's data within one source's json shape."""

from __future__ import annotations

from abc import ABC, abstractmethod

from tft_set_info_tools.schema.models import ExtractedSet
from tft_set_info_tools.schema.vocab import AugmentTier, ItemType


class SetDataSchema(ABC):
    """Interface for locating/classifying a set's data within one source's json shape."""

    @staticmethod
    @abstractmethod
    def matches(raw: dict) -> bool:
        """Whether raw looks like this schema's shape."""
        raise NotImplementedError

    def validate(self, raw: dict) -> None:
        """Raise ValueError unless raw actually matches this schema.

        Used when a TFTDataSource declares a schema via get_schema(): rather
        than silently trusting the source or re-sniffing, we assert the raw
        data really is what that source promised, so a shape drift (e.g. the
        upstream endpoint changing its json) fails loudly and specifically
        instead of surfacing as a confusing KeyError deeper in extract().
        """
        if not self.matches(raw):
            raise ValueError(
                f"Data does not match the expected {type(self).__name__} shape"
            )

    @abstractmethod
    def latest_set_number(self, raw: dict) -> int:
        """The highest set number present in raw."""
        raise NotImplementedError

    @abstractmethod
    def extract(self, raw: dict, set_num: int) -> ExtractedSet:
        """Locate the given set's data within raw. Raises ValueError if not found."""
        raise NotImplementedError

    @abstractmethod
    def item_matches(self, item: dict, item_type: ItemType) -> bool:
        raise NotImplementedError

    @abstractmethod
    def augment_matches(self, augment: dict, tier: AugmentTier) -> bool:
        raise NotImplementedError
