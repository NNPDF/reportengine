import functools
import pathlib
import pickle

def cache_to_file(directory: str="/tmp"):
    def inner(func):
        path = pathlib.Path(directory)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            suffix = pathlib.Path(func.__name__ + "(" + str(args) + ", "+ str(kwargs) + ")")
            cache_file = path / suffix

            if cache_file.exists():
                with open(cache_file, "rb") as in_stream:
                    cached_args, cached_kwargs, cached_result = pickle.load(in_stream)
                if cached_args == args and cached_kwargs == kwargs:
                    result = cached_result
            else:
                result = func(*args, **kwargs)
                with open(cache_file, 'wb') as out_stream:
                    to_cache = (args, kwargs, result)
                    pickle.dump(to_cache, out_stream, pickle.HIGHEST_PROTOCOL)

            return result
        return wrapper
    return inner
