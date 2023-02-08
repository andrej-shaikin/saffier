import sqlite3

import asyncpg
import pymysql
import pytest
from tests.settings import DATABASE_URL

import saffier
from saffier.core.db import Database

pytestmark = pytest.mark.anyio

database = Database(DATABASE_URL)
models = saffier.Registry(database=database)


class Album(saffier.Model):
    registry = models
    fields = {
        "id": saffier.IntegerField(primary_key=True),
        "name": saffier.CharField(max_length=100),
    }


class Track(saffier.Model):
    registry = models
    fields = {
        "id": saffier.IntegerField(primary_key=True),
        "album": saffier.ForeignKey("Album", on_delete=saffier.CASCADE),
        "title": saffier.CharField(max_length=100),
        "position": saffier.IntegerField(),
    }


class Organisation(saffier.Model):
    registry = models
    fields = {
        "id": saffier.IntegerField(primary_key=True),
        "ident": saffier.CharField(max_length=100),
    }


class Team(saffier.Model):
    registry = models
    fields = {
        "id": saffier.IntegerField(primary_key=True),
        "org": saffier.ForeignKey(Organisation, on_delete=saffier.RESTRICT),
        "name": saffier.CharField(max_length=100),
    }


class Member(saffier.Model):
    registry = models
    fields = {
        "id": saffier.IntegerField(primary_key=True),
        "team": saffier.ForeignKey(Team, on_delete=saffier.SET_NULL, null=True),
        "email": saffier.CharField(max_length=100),
    }


class Profile(saffier.Model):
    registry = models
    fields = {
        "id": saffier.IntegerField(primary_key=True),
        "website": saffier.CharField(max_length=100),
    }


class Person(saffier.Model):
    registry = models
    fields = {
        "id": saffier.IntegerField(primary_key=True),
        "email": saffier.CharField(max_length=100),
        "profile": saffier.OneToOneField(Profile),
    }


@pytest.fixture(autouse=True, scope="module")
async def create_test_database():
    await models.create_all()
    yield
    await models.drop_all()


@pytest.fixture(autouse=True)
async def rollback_connections():
    with database.force_rollback():
        async with database:
            yield


async def test_model_crud():
    album = await Album.query.create(name="Malibu")
    await Track.query.create(album=album, title="The Bird", position=1)
    await Track.query.create(album=album, title="Heart don't stand a chance", position=2)
    await Track.query.create(album=album, title="The Waters", position=3)

    track = await Track.query.get(title="The Bird")
    assert track.album.pk == album.pk
    assert not hasattr(track.album, "name")
    await track.album.load()
    assert track.album.name == "Malibu"


async def test_select_related():
    album = await Album.query.create(name="Malibu")
    await Track.query.create(album=album, title="The Bird", position=1)
    await Track.query.create(album=album, title="Heart don't stand a chance", position=2)
    await Track.query.create(album=album, title="The Waters", position=3)

    fantasies = await Album.query.create(name="Fantasies")
    await Track.query.create(album=fantasies, title="Help I'm Alive", position=1)
    await Track.query.create(album=fantasies, title="Sick Muse", position=2)
    await Track.query.create(album=fantasies, title="Satellite Mind", position=3)

    track = await Track.query.select_related("album").get(title="The Bird")
    assert track.album.name == "Malibu"

    tracks = await Track.query.select_related("album").all()
    assert len(tracks) == 6


async def test_fk_filter():
    malibu = await Album.query.create(name="Malibu")
    await Track.query.create(album=malibu, title="The Bird", position=1)
    await Track.query.create(album=malibu, title="Heart don't stand a chance", position=2)
    await Track.query.create(album=malibu, title="The Waters", position=3)

    fantasies = await Album.query.create(name="Fantasies")
    await Track.query.create(album=fantasies, title="Help I'm Alive", position=1)
    await Track.query.create(album=fantasies, title="Sick Muse", position=2)
    await Track.query.create(album=fantasies, title="Satellite Mind", position=3)

    tracks = await Track.query.select_related("album").filter(album__name="Fantasies").all()
    assert len(tracks) == 3
    for track in tracks:
        assert track.album.name == "Fantasies"

    tracks = await Track.query.select_related("album").filter(album__name__icontains="fan").all()
    assert len(tracks) == 3
    for track in tracks:
        assert track.album.name == "Fantasies"

    tracks = await Track.query.filter(album__name__icontains="fan").all()
    assert len(tracks) == 3
    for track in tracks:
        assert track.album.name == "Fantasies"

    tracks = await Track.query.filter(album=malibu).select_related("album").all()
    assert len(tracks) == 3
    for track in tracks:
        assert track.album.name == "Malibu"


async def test_multiple_fk():
    acme = await Organisation.query.create(ident="ACME Ltd")
    red_team = await Team.query.create(org=acme, name="Red Team")
    blue_team = await Team.query.create(org=acme, name="Blue Team")
    await Member.query.create(team=red_team, email="a@example.org")
    await Member.query.create(team=red_team, email="b@example.org")
    await Member.query.create(team=blue_team, email="c@example.org")
    await Member.query.create(team=blue_team, email="d@example.org")

    other = await Organisation.query.create(ident="Other ltd")
    team = await Team.query.create(org=other, name="Green Team")
    await Member.query.create(team=team, email="e@example.org")

    members = (
        await Member.query.select_related("team__org").filter(team__org__ident="ACME Ltd").all()
    )
    assert len(members) == 4
    for member in members:
        assert member.team.org.ident == "ACME Ltd"


async def test_queryset_delete_with_fk():
    malibu = await Album.query.create(name="Malibu")
    await Track.query.create(album=malibu, title="The Bird", position=1)

    wall = await Album.query.create(name="The Wall")
    await Track.query.create(album=wall, title="The Wall", position=1)

    await Track.query.filter(album=malibu).delete()
    assert await Track.query.filter(album=malibu).count() == 0
    assert await Track.query.filter(album=wall).count() == 1


async def test_queryset_update_with_fk():
    malibu = await Album.query.create(name="Malibu")
    wall = await Album.query.create(name="The Wall")
    await Track.query.create(album=malibu, title="The Bird", position=1)

    await Track.query.filter(album=malibu).update(album=wall)
    assert await Track.query.filter(album=malibu).count() == 0
    assert await Track.query.filter(album=wall).count() == 1


@pytest.mark.skipif(database.url.dialect == "sqlite", reason="Not supported on SQLite")
async def test_on_delete_cascade():
    album = await Album.query.create(name="The Wall")
    await Track.query.create(album=album, title="Hey You", position=1)
    await Track.query.create(album=album, title="Breathe", position=2)

    assert await Track.query.count() == 2

    await album.delete()

    assert await Track.query.count() == 0


@pytest.mark.skipif(database.url.dialect == "sqlite", reason="Not supported on SQLite")
async def test_on_delete_retstrict():
    organisation = await Organisation.query.create(ident="Encode")
    await Team.query.create(org=organisation, name="Maintainers")

    exceptions = (
        asyncpg.exceptions.ForeignKeyViolationError,
        pymysql.err.IntegrityError,
    )

    with pytest.raises(exceptions):
        await organisation.delete()


@pytest.mark.skipif(database.url.dialect == "sqlite", reason="Not supported on SQLite")
async def test_on_delete_set_null():
    organisation = await Organisation.query.create(ident="Encode")
    team = await Team.query.create(org=organisation, name="Maintainers")
    await Member.query.create(email="member@encode.io", team=team)

    await team.delete()

    member = await Member.query.first()
    assert member.team.pk is None


async def test_one_to_one_crud():
    profile = await Profile.query.create(website="https://encode.io")
    await Person.query.create(email="info@encode.io", profile=profile)

    person = await Person.query.get(email="info@encode.io")
    assert person.profile.pk == profile.pk
    assert not hasattr(person.profile, "website")

    await person.profile.load()
    assert person.profile.website == "https://encode.io"

    exceptions = (
        asyncpg.exceptions.UniqueViolationError,
        pymysql.err.IntegrityError,
        sqlite3.IntegrityError,
    )

    with pytest.raises(exceptions):
        await Person.query.create(email="contact@encode.io", profile=profile)


async def test_nullable_foreign_key():
    await Member.query.create(email="dev@encode.io")

    member = await Member.query.get()

    assert member.email == "dev@encode.io"
    assert member.team.pk is None
