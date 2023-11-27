import asyncio
import typing as t

from coges.coge import Coge
from loguru import logger


class MachineMeta(t.TypedDict):
    tick: t.Any
    active_coges: list[str]
    results: dict[str, t.Any]


TickFn = t.Generator[t.Any, t.Any, t.Any]
State = t.Union[t.Dict[str, t.Any], MachineMeta]
Machine = t.Callable[[], t.Coroutine[t.Any, t.Any, None]]


def identity(x: t.Any) -> t.Any:
    return x


def to_result(name_task: tuple[str, asyncio.Task]) -> tuple[str, bool]:
    return (name_task[0], name_task[1].result())


def by_result(name_result: tuple[str, bool]) -> bool:
    return name_result[1]


def to_name(name_result: tuple[str, bool]) -> str:
    return name_result[0]


async def choose_active_coges(
    coges: list[Coge], state: State, di_resolver
) -> list[Coge]:
    tasks: dict[str, asyncio.Task] = {}
    logger.debug("starting coges predicates")
    async with asyncio.TaskGroup() as tg:
        for _coge in coges:
            logger.debug(f"starting '{_coge.name}' predicate")
            tasks[_coge.name] = tg.create_task(
                di_resolver(_coge.get_predicate())(**state)
            )
    logger.debug("filtering coges by predicate results")
    result = list(
        filter(
            lambda coge: coge.name
            in map(
                to_name,
                filter(
                    by_result,
                    map(to_result, ((name, task) for name, task in tasks.items())),
                ),
            ),
            coges,
        )
    )
    logger.debug(f"finished filtering coges by predicate results: {result}")
    return result


def validate_coges(coges: list[Coge]) -> None:
    empty_predicates = list(filter(lambda coge: coge.get_predicate() is None, coges))
    empty_actions = list(filter(lambda coge: coge.get_action() is None, coges))

    if len(empty_predicates) > 0:
        raise ValueError(f"Coges with empty predicates: {empty_predicates}")

    if len(empty_actions) > 0:
        raise ValueError(f"Coges with empty actions: {empty_actions}")


def create_machine(
    coges: list[Coge], tick_fn: TickFn, di_resolver=identity, initial_state: State = {}
) -> Machine:
    validate_coges(coges)

    state: State = dict(tick=None, results=dict(), active_coges=list(), **initial_state)
    logger.debug(f"starting machine with coges: {coges}")

    async def __machine():
        for tick in tick_fn:
            logger.debug(f"new tick: '{tick}'")
            state.update({"tick": tick})
            logger.debug(f"choosing active coges for tick '{tick}'")
            active_coges = await choose_active_coges(coges, state, di_resolver)
            logger.debug(f"active coges for tick '{tick}': {active_coges}")
            results: dict[str, t.Any] = {}
            logger.debug(f"running active coges for tick '{tick}'")
            async with asyncio.TaskGroup() as tg:
                for _coge in active_coges:
                    logger.debug(f"running '{_coge.name}'")
                    results[_coge.name] = tg.create_task(
                        di_resolver(_coge.get_action())(**state)
                    )
                logger.debug(f"waiting for results of tick '{tick}'")

            logger.debug(f"finished waiting for results of tick '{tick}'")
            state.update(
                dict(
                    results=dict(
                        **{name: task.result() for name, task in results.items()}
                    )
                )
            )
            state.update({"active_coges": [coge.name for coge in active_coges]})
            logger.debug(f"tick {tick} results in: {state}")

    return __machine
