import inspect
import traceback
import ast


class _AssignChecker(ast.NodeVisitor):
    def __init__(self):
        self._assign_type = None

    def check(self, node):
        self.visit(node)
        return self._assign_type

    def visit_Assign(self, node):
        if isinstance(node.targets[0], ast.Tuple):
            self._assign_type = "unpacking"
        elif len(node.targets) > 1:
            self._assign_type = "multiple"
        else:
            self._assign_type = "single"
        self.generic_visit(node)


class _cached_property:
    """ A property that is only computed once per instance and then replaces
    itself with an ordinary attribute. Deleting the attribute resets the
    property.
    """
    def __init__(self, function):
        self.function = function

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.function.__name__] = self.function(obj)
        return value


class Object:
    """Make an object with the __name__ property."""
    def __init__(self):
        # !!!: the _get_name_from_traceback() method should be executed
        # in the __init__() method to work. May be this have some relation
        # with the traceback.extract_stack() method.
        self._from_traceback_name = self._get_name_from_traceback()

    def _get_name_from_traceback(self):
        """Find the name looking the code of the traceback."""
        if issubclass(type(self), Object) and not type(self) is Object:
            _stack_position = -4
        else:
            _stack_position = -3
        *_, code = traceback.extract_stack()[_stack_position]
        if code:
            try:
                tree = ast.parse(code)
                assign = _AssignChecker()
                assign_type = assign.check(tree)
                if assign_type == "multiple":
                    raise NotImplementedError(
                        "Can not assing a unique name to multiple variables.")
            except SyntaxError:
                # SyntaxError is raised if the line was broke.
                pass

            full_name, *_ = code.split('=')
            *_, name = full_name.split('.')
            return name.strip()
        else:
            return None

    def _get_outer_globals(self, frame):
        """Yield all global variables in the higher (calling) frames."""
        while frame:
            yield frame.f_globals
            frame = frame.f_back

    def _get_name_from_globals(self):
        """Find the name looking each superior global namespace."""
        global_variables = self._get_outer_globals(inspect.currentframe())
        for variables in global_variables:
            # CAVEAT: the same object could have many names. So I store all
            # in the names var.
            names = []
            for name, value in variables.items():
                if value is self:
                    names.append(name)
            if len(names) > 1:
                raise NotImplementedError(
                    "Can not assing a unique name to multiple variables.")
        if len(names) == 1:
            return names[0]
        else:
            raise RuntimeError("Can not found the name of this variable.")

    @_cached_property
    def __name__(self):
        """Find the name of the instance of the current class."""
        if self._from_traceback_name is None:
            return self._get_name_from_globals()
        else:
            return self._from_traceback_name

    # NOTE: I Can not override the __qualname__ property. That's an cpython
    # resctriction. See http://bugs.python.org/issue19073
    # @_cached_property
    # def __qualname__(self):
    #     return "%s.%s" % (self.__class__.__name__, self.__name__)
