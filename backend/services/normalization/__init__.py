"""Merchant normalization — collapses "Starbucks 徐家汇店" / "STARBUCKS #3341" /
"星巴克（南京西路店）" to one brand name so classification, learned rules and
duplicate detection all see a single merchant identity.

Strategy (PHASE_2.md, first match wins): user aliases → location/suffix
stripping → brand-table lookup → title-cased fallback.
"""
from backend.services.normalization.engine import NormalizationOutcome, normalize
from backend.services.normalization.strippers import strip_location

__all__ = ["NormalizationOutcome", "normalize", "strip_location"]
