import functools
import pickle

class comparepartial(functools.partial):
    def __eq__(self, other):
        return (isinstance(other, type(self)) and 
                self.func == other.func and self.args == other.args and
                self.keywords == other.keywords 
               )

    def __hash__(self):
        return hash(pickle.dumps(self))
