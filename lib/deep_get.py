def deep_get(data: dict, path: list, default=None):
    """Safely retrieve a nested value from a dict by key path."""
    for key in path:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data
