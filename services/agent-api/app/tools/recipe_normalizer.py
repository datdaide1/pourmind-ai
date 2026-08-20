"""Recipe normalizer (RCP-01).

Turns raw, bartender-entered recipe lines into the FND-02 domain
representation (`app.domain.schemas.IngredientLine`) deterministically, per
the MVP spec (docs/REGULAR_GUEST_INTELLIGENCE_MVP_SPEC.md, R3) and the RCP-01
task plan.

Design constraints:

* Only the five schema-approved units are ever produced: ``ml``, ``dash``,
  ``drop``, ``barspoon``, ``piece``. Common spellings, plurals and casing of
  those five are recognized deterministically (e.g. ``"Dashes"`` ->
  ``dash``). Anything else (``"oz"``, ``"tsp"``, ``"cl"``, ...) has no
  approved conversion factor in the spec and is reported unresolved rather
  than guessed.
* The bartender-entered ingredient text is preserved verbatim in
  ``display_name``. A ``normalized_ingredient_id`` is attached only when a
  caller-supplied ingredient registry has a matching entry; the normalizer
  never invents one.
* A line that cannot be normalized (unrecognized unit, unparseable or
  out-of-range amount, missing name) is never fabricated into an
  ``IngredientLine``. It is reported in ``unresolved`` with a reason, and
  noted in ``missing_data``, so a human can resolve it instead of the system
  silently dropping or guessing data.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Mapping, Sequence, Union

from pydantic import ValidationError

from app.domain.enums import IngredientUnit
from app.domain.schemas import IngredientLine

__all__ = [
    "RawIngredientLine",
    "IngredientRegistryEntry",
    "IngredientRegistry",
    "UnresolvedIngredientLine",
    "RecipeNormalizationResult",
    "resolve_unit",
    "normalize_recipe_ingredients",
]

Amount = Union[int, float, str]


# ---------------------------------------------------------------------------
# Unit registry: deterministic aliases -> the five schema-approved units.
# ---------------------------------------------------------------------------

_UNIT_ALIASES: dict[str, IngredientUnit] = {
    "ml": IngredientUnit.ML,
    "mls": IngredientUnit.ML,
    "milliliter": IngredientUnit.ML,
    "milliliters": IngredientUnit.ML,
    "millilitre": IngredientUnit.ML,
    "millilitres": IngredientUnit.ML,
    "dash": IngredientUnit.DASH,
    "dashes": IngredientUnit.DASH,
    "drop": IngredientUnit.DROP,
    "drops": IngredientUnit.DROP,
    "barspoon": IngredientUnit.BARSPOON,
    "barspoons": IngredientUnit.BARSPOON,
    "bar spoon": IngredientUnit.BARSPOON,
    "bar spoons": IngredientUnit.BARSPOON,
    "bsp": IngredientUnit.BARSPOON,
    "piece": IngredientUnit.PIECE,
    "pieces": IngredientUnit.PIECE,
    "pc": IngredientUnit.PIECE,
    "pcs": IngredientUnit.PIECE,
}
# The canonical enum spellings always resolve to themselves, even if a
# specific alias above were ever removed.
for _unit in IngredientUnit:
    _UNIT_ALIASES.setdefault(_unit.value, _unit)


def _normalize_lookup_key(raw: str) -> str:
    """Canonicalize text for case/whitespace/Unicode-form-insensitive lookups.

    NFKC + casefold + whitespace collapse is a lossless canonicalization, not
    a guess: it never merges two spellings that use genuinely different
    characters (accents and other diacritics are preserved).
    """
    text = unicodedata.normalize("NFKC", raw).strip().casefold()
    return re.sub(r"\s+", " ", text)


def resolve_unit(raw_unit: str) -> IngredientUnit | None:
    """Resolve a raw unit string to one of the five approved units, or None."""
    if not isinstance(raw_unit, str) or not raw_unit.strip():
        return None
    return _UNIT_ALIASES.get(_normalize_lookup_key(raw_unit))


# ---------------------------------------------------------------------------
# Ingredient registry: optional, caller-supplied known-ingredient lookup.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IngredientRegistryEntry:
    id: str
    name: str


class IngredientRegistry:
    """Case/whitespace/Unicode-form-insensitive known-ingredient lookup.

    The normalizer never invents a ``normalized_ingredient_id``; it only
    resolves one when the caller-supplied registry has an exact
    (canonicalized) name match. An empty registry means every ingredient is
    reported as unresolved, which is intentional when no reference data has
    been supplied yet.
    """

    def __init__(
        self,
        entries: Iterable[IngredientRegistryEntry | Mapping[str, str]] = (),
    ) -> None:
        self._by_key: dict[str, IngredientRegistryEntry] = {}
        for entry in entries:
            self.register(entry)

    def register(self, entry: IngredientRegistryEntry | Mapping[str, str]) -> None:
        if not isinstance(entry, IngredientRegistryEntry):
            entry = IngredientRegistryEntry(id=str(entry["id"]), name=str(entry["name"]))
        key = _normalize_lookup_key(entry.name)
        if key:
            self._by_key[key] = entry

    def resolve(self, raw_name: str) -> IngredientRegistryEntry | None:
        if not isinstance(raw_name, str) or not raw_name.strip():
            return None
        return self._by_key.get(_normalize_lookup_key(raw_name))


_EMPTY_REGISTRY = IngredientRegistry()


# ---------------------------------------------------------------------------
# Amount parsing: decimals and bartender-style fractions only. No unit math.
# ---------------------------------------------------------------------------

_FRACTION_PATTERN = re.compile(r"^(?:(?P<whole>\d+)\s+)?(?P<num>\d+)\s*/\s*(?P<den>\d+)$")


def _parse_amount(raw_amount: object) -> float | None:
    """Parse an amount into a float without inventing precision.

    Accepts ints/floats, plain decimal strings (``"1.5"``), and
    bartender-style fractions (``"1/2"``, ``"1 1/2"``). Anything else
    (non-numeric text, booleans, empty values) is unresolved rather than
    coerced.
    """
    if isinstance(raw_amount, bool):
        return None
    if isinstance(raw_amount, (int, float)):
        return float(raw_amount)
    if not isinstance(raw_amount, str):
        return None

    text = raw_amount.strip()
    if not text:
        return None

    match = _FRACTION_PATTERN.match(text)
    if match:
        den = int(match.group("den"))
        if den == 0:
            return None
        whole = int(match.group("whole")) if match.group("whole") else 0
        return float(whole + Fraction(int(match.group("num")), den))

    try:
        return float(text)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RawIngredientLine:
    """A single bartender-entered ingredient line, before normalization."""

    display_name: str
    amount: Amount
    unit: str


@dataclass(frozen=True)
class UnresolvedIngredientLine:
    """A raw line that could not be turned into a valid ``IngredientLine``."""

    index: int
    display_name: str
    raw_amount: Amount
    raw_unit: str
    reason: str  # "missing_display_name" | "unrecognized_unit" | "invalid_amount"


@dataclass(frozen=True)
class RecipeNormalizationResult:
    ingredients: list[IngredientLine]
    unresolved: list[UnresolvedIngredientLine]
    missing_data: list[str]


def _coerce_raw_line(raw: "RawIngredientLine | Mapping[str, object]") -> RawIngredientLine:
    if isinstance(raw, RawIngredientLine):
        return raw
    return RawIngredientLine(
        display_name=str(raw.get("display_name", "")),
        amount=raw.get("amount"),  # type: ignore[arg-type]
        unit=str(raw.get("unit", "")),
    )


def normalize_recipe_ingredients(
    raw_lines: Sequence["RawIngredientLine | Mapping[str, object]"],
    *,
    ingredient_registry: IngredientRegistry | None = None,
) -> RecipeNormalizationResult:
    """Normalize raw recipe ingredient lines into ``IngredientLine`` entries.

    Every input line is processed independently and in order, so duplicate
    ingredient names (e.g. gin poured twice in one recipe) each produce their
    own resolved (or unresolved) line rather than being merged or dropped.
    """
    registry = ingredient_registry if ingredient_registry is not None else _EMPTY_REGISTRY

    ingredients: list[IngredientLine] = []
    unresolved: list[UnresolvedIngredientLine] = []
    missing_data: list[str] = []

    for index, raw in enumerate(raw_lines):
        line = _coerce_raw_line(raw)
        display_name = line.display_name.strip() if isinstance(line.display_name, str) else ""

        if not display_name:
            unresolved.append(
                UnresolvedIngredientLine(
                    index=index,
                    display_name=line.display_name,
                    raw_amount=line.amount,
                    raw_unit=line.unit,
                    reason="missing_display_name",
                )
            )
            missing_data.append(f"ingredient[{index}]: display name is missing")
            continue

        unit = resolve_unit(line.unit)
        if unit is None:
            unresolved.append(
                UnresolvedIngredientLine(
                    index=index,
                    display_name=display_name,
                    raw_amount=line.amount,
                    raw_unit=line.unit,
                    reason="unrecognized_unit",
                )
            )
            missing_data.append(
                f"ingredient[{index}] {display_name!r}: unit {line.unit!r} is not a supported unit"
            )
            continue

        amount = _parse_amount(line.amount)
        if amount is None:
            unresolved.append(
                UnresolvedIngredientLine(
                    index=index,
                    display_name=display_name,
                    raw_amount=line.amount,
                    raw_unit=line.unit,
                    reason="invalid_amount",
                )
            )
            missing_data.append(
                f"ingredient[{index}] {display_name!r}: amount {line.amount!r} could not be parsed"
            )
            continue

        registry_entry = registry.resolve(display_name)
        try:
            ingredient = IngredientLine(
                display_name=display_name,
                normalized_ingredient_id=registry_entry.id if registry_entry else None,
                amount=amount,
                unit=unit,
            )
        except ValidationError:
            unresolved.append(
                UnresolvedIngredientLine(
                    index=index,
                    display_name=display_name,
                    raw_amount=line.amount,
                    raw_unit=line.unit,
                    reason="invalid_amount",
                )
            )
            missing_data.append(
                f"ingredient[{index}] {display_name!r}: amount {line.amount!r} is out of the supported range"
            )
            continue

        ingredients.append(ingredient)
        if registry_entry is None:
            missing_data.append(
                f"ingredient[{index}] {display_name!r}: no matching normalized ingredient id"
            )

    return RecipeNormalizationResult(
        ingredients=ingredients,
        unresolved=unresolved,
        missing_data=missing_data,
    )
