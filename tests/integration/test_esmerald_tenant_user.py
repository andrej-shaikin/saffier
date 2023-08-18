from typing import Any, AsyncGenerator, Coroutine

import pytest
from anyio import from_thread, sleep, to_thread
from esmerald import Esmerald, Gateway, JSONResponse, Request, get
from esmerald.protocols.middleware import MiddlewareProtocol
from httpx import AsyncClient
from pydantic import __version__
from starlette.types import ASGIApp, Receive, Scope, Send

from saffier.contrib.multi_tenancy import TenantModel, TenantRegistry
from saffier.contrib.multi_tenancy.models import TenantMixin, TenantUserMixin
from saffier.core.db import fields, set_tenant
from saffier.exceptions import ObjectNotFound
from saffier.testclient import DatabaseTestClient as Database
from tests.settings import DATABASE_URL

database = Database(url=DATABASE_URL)
models = TenantRegistry(database=database)


pytestmark = pytest.mark.anyio
pydantic_version = __version__[:3]


class Tenant(TenantMixin):
    class Meta:
        registry = models


class User(TenantModel):
    id: int = fields.IntegerField(primary_key=True)
    name: str = fields.CharField(max_length=255)
    email: str = fields.EmailField(max_length=255)

    class Meta:
        registry = models
        is_tenant = True


class Product(TenantModel):
    id: int = fields.IntegerField(primary_key=True)
    name: str = fields.CharField(max_length=255)
    user: User = fields.ForeignKey(User, null=True)

    class Meta:
        registry = models
        is_tenant = True


class TenantUser(TenantUserMixin):
    user = fields.ForeignKey(
        "User", null=False, blank=False, related_name="tenant_user_users_test"
    )
    tenant = fields.ForeignKey(
        "Tenant", null=False, blank=False, related_name="tenant_users_tenant_test"
    )

    class Meta:
        registry = models


class TenantMiddleware(MiddlewareProtocol):
    def __init__(self, app: "ASGIApp"):
        super().__init__(app)
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> Coroutine[Any, Any, None]:
        request = Request(scope=scope, receive=receive, send=send)

        tenant_header = request.headers.get("tenant", None)
        tenant_email = request.headers.get("email", None)

        try:
            _tenant = await Tenant.query.get(schema_name=tenant_header)
            user = await User.query.get(email=tenant_email)

            await TenantUser.query.get(tenant=_tenant, user=user)
            tenant = _tenant.schema_name
        except ObjectNotFound:
            tenant = None

        set_tenant(tenant)
        await self.app(scope, receive, send)


@pytest.fixture(autouse=True, scope="function")
async def create_test_database():
    try:
        await models.create_all()
        yield
        await models.drop_all()
    except Exception:
        pytest.skip("No database available")


@pytest.fixture(autouse=True)
async def rollback_connections():
    with database.force_rollback():
        async with database:
            yield


def blocking_function():
    from_thread.run(sleep, 0.1)


@get("/products")
async def get_products() -> JSONResponse:
    products = await Product.query.all()
    products = [product.pk for product in products]
    return JSONResponse(products)


@pytest.fixture()
def app():
    app = Esmerald(
        routes=[Gateway(handler=get_products)],
        middleware=[TenantMiddleware],
        on_startup=[database.connect],
        on_shutdown=[database.disconnect],
    )
    return app


@pytest.fixture()
def another_app():
    app = Esmerald(
        routes=[Gateway("/no-tenant", handler=get_products)],
        on_startup=[database.connect],
        on_shutdown=[database.disconnect],
    )
    return app


@pytest.fixture()
async def async_cli(another_app) -> AsyncGenerator:
    async with AsyncClient(app=another_app, base_url="http://test") as acli:
        await to_thread.run_sync(blocking_function)
        yield acli


@pytest.fixture()
async def async_client(app) -> AsyncGenerator:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await to_thread.run_sync(blocking_function)
        yield ac


async def create_data():
    """
    Creates mock data
    """
    saffier = await User.query.create(name="saffier", email="saffier@esmerald.dev")
    user = await User.query.create(name="edgy", email="edgy@esmerald.dev")
    edgy_tenant = await Tenant.query.create(schema_name="saffier", tenant_name="saffier")

    saffier = await User.query.using(edgy_tenant.schema_name).create(
        name="saffier", email="saffier@esmerald.dev"
    )

    await TenantUser.query.create(user=saffier, tenant=edgy_tenant)

    # Products for Edgy
    for i in range(10):
        await Product.query.using(edgy_tenant.schema_name).create(
            name=f"Product-{i}", user=saffier
        )

    # Products for Saffier
    for i in range(25):
        await Product.query.create(name=f"Product-{i}", user=user)


async def test_user_query_tenant_data(async_client, async_cli):
    await create_data()

    # Test Edgy Response intercepted in the
    response_edgy = await async_client.get(
        "/products", headers={"tenant": "saffier", "email": "saffier@esmerald.dev"}
    )
    assert response_edgy.status_code == 200

    assert len(response_edgy.json()) == 10

    # Test Edgy Response intercepted in the
    response_saffier = await async_client.get("/products")
    assert response_saffier.status_code == 200

    assert len(response_saffier.json()) == 25

    # Check saffier again
    response_edgy = await async_client.get(
        "/products", headers={"tenant": "saffier", "email": "saffier@esmerald.dev"}
    )
    assert response_edgy.status_code == 200

    assert len(response_edgy.json()) == 10

    response = await async_cli.get("/no-tenant/products")
    assert response.status_code == 200
    assert len(response.json()) == 25
