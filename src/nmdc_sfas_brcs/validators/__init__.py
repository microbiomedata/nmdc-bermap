"""Validators for LinkML schemas."""

__all__ = ["EnumEvaluator", "ValidationConfig", "ValidationResult"]


def __getattr__(name):
    if name in __all__:
        from .enum_evaluator import EnumEvaluator, ValidationConfig, ValidationResult

        values = {
            "EnumEvaluator": EnumEvaluator,
            "ValidationConfig": ValidationConfig,
            "ValidationResult": ValidationResult,
        }
        return values[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
