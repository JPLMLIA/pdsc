"""
Miscellaneous utilities
"""
from progressbar import ProgressBar, ETA, Bar

def registerer(registration_dict):
    def register_to_instrument(instrument):
        def decorator(obj):
            registration_dict[instrument] = obj
            return obj
        return decorator
    return register_to_instrument

def standard_progress_bar(message, verbose=True):
    if verbose:
        progress = ProgressBar(widgets=[
            '%s: ' % message, Bar('='), ' ', ETA()
        ])
        return progress
    else:
        return (lambda x: x)
