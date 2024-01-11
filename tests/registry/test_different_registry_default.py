from datetime import datetime
from enum import Enum

import pytest

import saffier
from saffier.core.db import fields
from saffier.testclient import DatabaseTestClient as Database
from tests.settings import DATABASE_URL

pytestmark = pytest.mark.anyio

database = Database(DATABASE_URL)
models = saffier.Registry(database=database, schema="another")


def time():
    return datetime.now().time()


class StatusEnum(Enum):
    DRAFT = "Draft"
    RELEASED = "Released"


class Product(saffier.Model):
    id = fields.IntegerField(primary_key=True)
    name = fields.CharField(max_length=255)

    class Meta:
        registry = models


@pytest.fixture(autouse=True, scope="module")
async def create_test_database():
    await models.create_all()
    yield
    await models.drop_all()


@pytest.fixture(autouse=True)
async def rollback_transactions():
    with database.force_rollback():
        async with database:
            yield


async def test_bulk_create():
    await Product.query.bulk_create(
        [
            {"name": "product-1"},
            {"name": "product-2"},
        ]
    )

    total = await Product.query.all()

    assert len(total) == 2
    assert Product.table.schema == models.db_schema
