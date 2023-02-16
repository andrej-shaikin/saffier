import pytest
from tests.settings import DATABASE_URL

import saffier
from saffier.db.connection import Database

database = Database(url=DATABASE_URL)
models = saffier.Registry(database=database)

pytestmark = pytest.mark.anyio


class User(saffier.Model):
    id = saffier.IntegerField(primary_key=True)
    name = saffier.CharField(max_length=100)
    language = saffier.CharField(max_length=200, null=True)

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


async def test_model_count():
    await User.query.create(name="Test")
    await User.query.create(name="Jane")
    await User.query.create(name="Lucy")

    assert await User.query.count() == 3
    assert await User.query.filter(name__icontains="T").count() == 1
