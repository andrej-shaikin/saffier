import pytest

import saffier
from saffier.testclient import DatabaseTestClient as Database
from tests.settings import DATABASE_URL

database = Database(url=DATABASE_URL)
models = saffier.Registry(database=database)

pytestmark = pytest.mark.anyio


class User(saffier.Model):
    id = saffier.IntegerField(primary_key=True)
    name = saffier.CharField(max_length=100)
    language = saffier.CharField(max_length=200, null=True)

    class Meta:
        registry = models


class Product(saffier.Model):
    id = saffier.IntegerField(primary_key=True)
    name = saffier.CharField(max_length=100)
    rating = saffier.IntegerField(minimum=1, maximum=5)
    in_stock = saffier.BooleanField(default=False)

    class Meta:
        registry = models
        name = "products"


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


async def test_queryset_update():
    shirt = saffier.run_sync(Product.query.create(name="Shirt", rating=5))
    tie = saffier.run_sync(Product.query.create(name="Tie", rating=5))

    saffier.run_sync(Product.query.filter(pk=shirt.id).update(rating=3))
    shirt = saffier.run_sync(Product.query.get(pk=shirt.id))
    assert shirt.rating == 3
    assert saffier.run_sync(Product.query.get(pk=tie.id)) == tie

    saffier.run_sync(Product.query.update(rating=3))
    tie = saffier.run_sync(Product.query.get(pk=tie.id))
    assert tie.rating == 3


async def test_model_update_or_create():
    user, created = saffier.run_sync(
        User.query.update_or_create(name="Test", language="English", defaults={"name": "Jane"})
    )
    assert created is True
    assert user.name == "Jane"
    assert user.language == "English"

    user, created = saffier.run_sync(
        User.query.update_or_create(name="Jane", language="English", defaults={"name": "Test"})
    )
    assert created is False
    assert user.name == "Test"
    assert user.language == "English"
