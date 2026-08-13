"""
Data schemas for menu extraction.
Using Pydantic v2 for validation.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator

class MenuItem(BaseModel):
    """
    Represents a single menu item.
    """
    name: str = Field(..., description="Name of the dish or drink")
    description: Optional[str] = Field(
        None, description="Description if provided on the menu"
    )
    price: Optional[float] = Field(
        None, description="Price as a number. Null if not visible."
    )
    currency: str = Field(
        default="INR", description="Currency code (INR, USD, etc.)"
    )
    category: Optional[str] = Field(
        None,
        description="Menu section: appetizer, main, dessert, beverage, side, etc."
    )
    ingredients: list[str] = Field(
        default_factory=list,
        description="Ingredients listed OR inferred from the dish name"
    )
    dietary_tags: list[str] = Field(
        default_factory=list,
        description="e.g. vegetarian, vegan, non-vegetarian, jain, gluten-free"
    )
    allergens: list[str] = Field(
        default_factory=list,
        description="e.g. dairy, nuts, gluten, eggs, shellfish"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Model's confidence in the extraction (0-1)"
    )

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError("Price cannot be negative")
        return v


class Menu(BaseModel):
    """A complete menu with all extracted items."""
    restaurant_name: Optional[str] = None
    items: list[MenuItem]
    source_notes: Optional[str] = Field(
        None, description="Any notes about extraction quality"
    )

    @property
    def item_count(self) -> int:
        return len(self.items)

    def by_category(self) -> dict[str, list[MenuItem]]:
        """Group items by category."""
        grouped: dict[str, list[MenuItem]] = {}
        for item in self.items:
            cat = item.category or "uncategorized"
            grouped.setdefault(cat, []).append(item)
        return grouped
   