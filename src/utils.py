import functools
import pickle

class Reflector:
        """A mixint that causes the constructor to return the argument
        if it is of the same type of the class when it is called with
        only one argument."""
        def __new__(cls, *args, **kwargs):
            if len(args)==1 and not kwargs:
                obj = args[0]
                if type(obj) is cls:
                    return obj
            return super().__new__(cls, *args, **kwargs)


class comparepartial(functools.partial):
    def __eq__(self, other):
        return (isinstance(other, type(self)) and 
                self.func == other.func and self.args == other.args and
                self.keywords == other.keywords 
               )

    def __hash__(self):
        return hash(pickle.dumps(self))


def partialkey(partial):
    return pickle.dumps(partial)

if __name__ == '__main__':
    class X(Reflector):
        pass
    x = X()
    assert(x is X(x))
