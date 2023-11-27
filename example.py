import asyncio
import random
import typing as t

from loguru import logger

from coges.coge import create_coge
from coges.di import create_dependency_injector
from coges.machine import MachineMeta, State, create_machine


test_coge = create_coge("test")
add, resolve = create_dependency_injector()


@add("weird_one")
def weird_one(logger):
    print("weird setting up")

    async def weird(something):
        logger.warning(f"async weird {something}")

    yield weird
    print("weird tearing down")


@add("logger")
def log():
    print("setting up")
    yield logger
    print("tearing down")


@test_coge.predicate
async def test_predicate(weird_one, results, **state):
    await weird_one("hello")
    return state.get("tick") == "hello"


@test_coge.action
async def test_action(logger, **state: t.Unpack[MachineMeta]):
    logger.info("test_action")
    return random.choice(["hey, dumbass", "howdy", "hello fellow kids"])


def tick_fn():
    for i in range(3):
        yield input("-> ")


machine = create_machine([test_coge], tick_fn(), resolve)


if __name__ == "__main__":
    asyncio.run(machine())
