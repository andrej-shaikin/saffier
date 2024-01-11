import pytest
from pydantic import __version__

import saffier
from saffier.contrib.multi_tenancy import TenantModel, TenantRegistry
from saffier.contrib.multi_tenancy.models import TenantMixin
from saffier.testclient import DatabaseTestClient as Database
from tests.settings import DATABASE_URL

database = Database(url=DATABASE_URL)
models = TenantRegistry(database=database)


pytestmark = pytest.mark.anyio
pydantic_version = __version__[:3]


class Tenant(TenantMixin):
    class Meta:
        registry = models


class EdgyTenantBaseModel(TenantModel):
    id: int = saffier.IntegerField(primary_key=True)

    class Meta:
        is_tenant = True
        registry = models
        abstract = True


class Designation(EdgyTenantBaseModel):
    name: str = saffier.CharField(max_length=100)

    class Meta:
        tablename = "ut_designation"


class AppModule(EdgyTenantBaseModel):
    name: str = saffier.CharField(max_length=100)

    class Meta:
        tablename = "ut_module"


class Permission(EdgyTenantBaseModel):
    module = saffier.ForeignKey(AppModule)
    designation = saffier.ForeignKey("Designation")
    can_read = saffier.BooleanField(default=False)
    can_write = saffier.BooleanField(default=False)
    can_update = saffier.BooleanField(default=False)
    can_delete = saffier.BooleanField(default=False)
    can_approve = saffier.BooleanField(default=False)

    class Meta:
        tablename = "ut_permission"


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


async def test_select_related():
    designation = await Designation.query.create(name="admin")
    module = await AppModule.query.create(name="payroll")

    permission = await Permission.query.create(designation=designation, module=module)

    query = await Permission.query.all()

    assert len(query) == 1

    query = await Permission.query.select_related(["designation", "module"]).all()

    assert len(query) == 1
    assert query[0].pk == permission.pk

    assert query[0].designation.model_dump() == {"id": 1, "name": "admin"}
    assert query[0].module.model_dump() == {"id": 1, "name": "payroll"}
