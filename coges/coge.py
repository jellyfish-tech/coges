import typing as t


Params = t.ParamSpec("Params")


PredicateFn = t.Callable[Params, t.Coroutine[t.Any, t.Any, bool]]
ActionFn = t.Callable[Params, t.Coroutine[t.Any, t.Any, t.Any]]


class CogeError(Exception):
    pass


class Coge:
    name: str
    __predicate: PredicateFn | None = None
    __action: ActionFn | None = None

    def __init__(self, name: str):
        self.name = name

    def predicate(self, predicate_fn: PredicateFn) -> None:
        self.__predicate = predicate_fn

    def action(self, action_fn: ActionFn) -> None:
        self.__action = action_fn

    def get_predicate(self) -> PredicateFn | None:
        return self.__predicate

    def get_action(self) -> ActionFn | None:
        return self.__action

    def __repr__(self):
        return f"<Coge: {self.name} predicate={self.get_predicate()} action={self.get_action()}>"


def create_coge(name: str) -> Coge:
    return Coge(name)
