"""
Miscellaneous utilities
"""
from progressbar import ProgressBar, ETA, Bar

def registerer(registration_dict):
    """
    Creates a decorator that will "register" a method or class to a particular
    instrument. The registration decorators are used to extend PDSC to other
    instruments.

    :param registration_dict:
        a dictionary to which the decorated function will be registered

    :return: registration decorator that assigns decorated function or class to
        the ``registration_dict`` keyed by a particular instrument, which is a
        required decorator argument
    """
    def register_to_instrument(instrument):
        def decorator(obj):
            registration_dict[instrument] = obj
            return obj
        return decorator
    return register_to_instrument

def standard_progress_bar(message, verbose=True):
    """
    Optionally constructs a standard :py:class:`progressbar.ProgressBar` used
    through PDSC

    :param message:
        progress message to display
    :param verbose:
        whether to display progress

    :return: a :py:class:`progressbar.ProgressBar` object if ``verbose=True``,
        or an identify function that can be used to omit progress
    """
    if verbose:
        progress = ProgressBar(widgets=[
            '%s: ' % message, Bar('='), ' ', ETA()
        ])
        return progress
    else:
        return (lambda x: x)
