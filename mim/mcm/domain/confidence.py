from dataclasses import dataclass

@dataclass(frozen=True)
class Confidence:
    """Value Object que representa confiança, com invariante 0.0 <= value <= 1.0."""
    value: float

    def __post_init__(self):
        if not (0.0 <= self.value <= 1.0):
            raise ValueError("Confidence value must be between 0.0 and 1.0")
