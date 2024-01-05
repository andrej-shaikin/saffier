import pytest

import saffier
from saffier.exceptions import QuerySetError
from saffier.testclient import DatabaseTestClient as Database
from tests.settings import DATABASE_URL

database = Database(url=DATABASE_URL)
models = saffier.Registry(database=database)

pytestmark = pytest.mark.anyio


class User(saffier.Model):
    id = saffier.IntegerField(primary_key=True)
    name = saffier.CharField(max_length=100)
    language = saffier.CharField(max_length=200, null=True)
    description = saffier.TextField(max_length=5000, null=True)

    class Meta:
        registry = models


@pytest.fixture(autouse=True, scope="function")
async def create_test_database():
    await models.create_all()
    yield
    await models.drop_all()


@pytest.fixture(autouse=True)
async def rollback_connections():
    with database.force_rollback():
        async with database:
            yield


@pytest.mark.parametrize(
    "value", [1, {"name": 1}, (1,), {"saffier"}], ids=["as-int", "as-dict", "as-tuple", "as-set"]
)
async def test_raise_exception(value):
    with pytest.raises(QuerySetError):
        saffier.run_sync(User.query.values(value))


async def test_model_values():
    saffier.run_sync(
        User.query.create(name="John", language="PT", description="A simple description")
    )
    saffier.run_sync(
        User.query.create(name="Jane", language="EN", description="Another simple description")
    )

    users = saffier.run_sync(User.query.values())

    assert len(users) == 2

    assert users == [
        {"id": 1, "name": "John", "language": "PT", "description": "A simple description"},
        {"id": 2, "name": "Jane", "language": "EN", "description": "Another simple description"},
    ]


async def test_model_values_list_fields():
    saffier.run_sync(User.query.create(name="John", language="PT"))
    saffier.run_sync(
        User.query.create(name="Jane", language="EN", description="Another simple description")
    )

    users = saffier.run_sync(User.query.values(["name"]))

    assert len(users) == 2

    assert users == [{"name": "John"}, {"name": "Jane"}]


async def test_model_values_exclude_fields():
    saffier.run_sync(User.query.create(name="John", language="PT"))
    saffier.run_sync(
        User.query.create(name="Jane", language="EN", description="Another simple description")
    )

    users = saffier.run_sync(User.query.values(exclude=["name", "id"]))
    assert len(users) == 2

    assert users == [
        {"language": "PT", "description": None},
        {"language": "EN", "description": "Another simple description"},
    ]


async def test_model_values_exclude_and_include_fields():
    saffier.run_sync(User.query.create(name="John", language="PT"))
    saffier.run_sync(
        User.query.create(name="Jane", language="EN", description="Another simple description")
    )

    users = saffier.run_sync(User.query.values(["id"], exclude=["name"]))
    assert len(users) == 2

    assert users == [{"id": 1}, {"id": 2}]


async def test_model_values_exclude_none():
    saffier.run_sync(User.query.create(name="John", language="PT"))
    saffier.run_sync(
        User.query.create(name="Jane", language="EN", description="Another simple description")
    )

    users = saffier.run_sync(User.query.values(exclude_none=True))
    assert len(users) == 2

    assert users == [
        {"id": 1, "name": "John", "language": "PT"},
        {"id": 2, "name": "Jane", "language": "EN", "description": "Another simple description"},
    ]


async def test_model_only_with_filter():
    saffier.run_sync(User.query.create(name="John", language="PT"))
    saffier.run_sync(
        User.query.create(name="Jane", language="EN", description="Another simple description")
    )

    users = saffier.run_sync(User.query.filter(id=2).values(["name"]))
    assert len(users) == 1

    assert users == [{"name": "Jane"}]

    users = saffier.run_sync(User.query.filter(id=3).values(["name"]))

    assert len(users) == 0

    assert users == []
