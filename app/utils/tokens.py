"""
Token counting utilities.

Extracts token usage from upstream model responses. Accepts either a dict
(OpenRouter / OpenAI style) or an object with attributes (legacy SDK shape).
"""


def _get_field(obj, *names, default=0):
    if obj is None:
        return default
    for name in names:
        if isinstance(obj, dict):
            value = obj.get(name)
        else:
            value = getattr(obj, name, None)
        if value is not None:
            return value
    return default


def extract_token_counts(usage) -> tuple[int, int, int]:
    """Extract token counts from an upstream usage payload.

    Args:
        usage: dict or object containing usage info.

    Returns:
        tuple: (input_tokens, output_tokens, total_tokens)
    """
    input_tokens = _get_field(
        usage, "prompt_tokens", "prompt_token_count", "promptTokenCount"
    )
    output_tokens = _get_field(
        usage, "completion_tokens", "candidates_token_count", "candidatesTokenCount"
    )
    total_tokens = _get_field(
        usage, "total_tokens", "total_token_count", "totalTokenCount"
    )
    return input_tokens, output_tokens, total_tokens
