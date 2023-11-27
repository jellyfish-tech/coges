import logging
import inspect
from functools import lru_cache, partial

logger = logging.getLogger(__name__)


def __async_partial(fn, *args, **kwargs):
    async def inner(*fargs, **fkwargs):
        return await fn(*args, *fargs, **kwargs, **fkwargs)

    return inner


# TODO: maybe value of a dependency itself might be inner class with __call__, __index__, __getattr__ etc methods implemented. That will allow
# TODO: dependencies to be truly lazy and waking up only on usage, not when they are present in parameters
class Dependency:
    def __init__(self, resolver):
        self.name = ""
        self.__resolver = resolver
        self.__factory = (None for _ in range(1))
        self.__instance = None
        self.__value = None

    def __wake_up(self):
        self.__instance = self.__resolver(self.factory)()
        self.__value = next(self.__instance)

    # FIXME: that's a mess of properties, handle in next iteration
    @property
    def factory(self):
        return self.__factory

    @factory.setter
    def factory(self, factory):
        self.__factory = factory

    @property
    def instance(self):
        return self.__instance

    @instance.setter
    def instance(self, value):
        self.__instance = value

    @instance.deleter
    def instance(self):
        if self.__instance is None:
            raise RuntimeError(f"{self.name} was never used")

        try:
            next(self.__instance)
        except StopIteration:
            del self.__instance
        else:
            raise RuntimeError(
                f"{self.name} instance is not exhausted. Factory should contain only one yield statement"
            )

    @property
    def value(self):
        self.__wake_up() if self.__instance is None else None
        return self.__value

    def __repr__(self):
        return "<Dependency: {}>".format(self.name)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name

    def __del__(self):
        del self.instance


def create_dependency_injector():  # noqa: C901 sue me
    dependencies: set[Dependency] = set()

    def resolve(fn):
        fn_parameters = inspect.signature(fn).parameters
        available_dependencies = filter(lambda d: d.name in fn_parameters, dependencies)

        partial_kind = __async_partial if inspect.iscoroutinefunction(fn) else partial

        return partial_kind(fn, **{d.name: d.value for d in available_dependencies})

    def add_dependency(name_or_factory):
        new_dependency = Dependency(resolver=resolve)

        if inspect.isgeneratorfunction(name_or_factory):
            new_dependency.name = name_or_factory.__name__
            new_dependency.factory = name_or_factory

            dependencies.add(new_dependency)

            return name_or_factory

        if isinstance(name_or_factory, str):

            def decorator(fn):
                new_dependency.name = name_or_factory
                new_dependency.factory = fn

                dependencies.add(new_dependency)

                return fn

            return decorator

    return add_dependency, resolve
