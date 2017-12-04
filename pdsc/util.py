"""
Miscellaneous utilities
"""

def registerer(registration_dict):
    def register_to_instrument(instrument):
        def decorator(obj):
            registration_dict[instrument] = obj
            return obj
        return decorator
    return register_to_instrument
