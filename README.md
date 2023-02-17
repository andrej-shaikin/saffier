# Saffier

<p align="center">
  <a href="https://saffier.tarsild.io"><img src="https://res.cloudinary.com/dymmond/image/upload/v1675104815/Saffier/logo/logo_dowatx.png" alt='Saffier'></a>
</p>

<p align="center">
    <em>🚀 The only Async ORM you need. 🚀</em>
</p>

<p align="center">
<a href="https://github.com/tarsil/saffier/workflows/Test%20Suite/badge.svg?event=push&branch=main" target="_blank">
    <img src="https://github.com/tarsil/saffier/workflows/Test%20Suite/badge.svg?event=push&branch=main" alt="Test Suite">
</a>

<a href="https://pypi.org/project/saffier" target="_blank">
    <img src="https://img.shields.io/pypi/v/saffier?color=%2334D058&label=pypi%20package" alt="Package version">
</a>

<a href="https://pypi.org/project/saffier" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/saffier.svg?color=%2334D058" alt="Supported Python versions">
</a>
</p>

---

**Documentation**: [https://saffier.tarsild.io](https://saffier.tarsild.io) 📚

**Source Code**: [https://github.com/tarsil/saffier](https://github.com/tarsil/saffier)

---

## Motivation

Almost every project, in one way or another uses one (or many) databases. An ORM is simply an mapping
of the top of an existing database. ORM extends for Object Relational Mapping and bridges object-oriented
programs and relational databases.

Two of the most well known ORMs are from Django and SQLAlchemy. Both have their own strenghts and
weaknesses and specific use cases.

This ORM is built on the top of SQLAlchemy core and aims to simplify the way the setup and queries
are done into a more common and familiar interface.

## Why this ORM

When investigating for a project different types of ORMs and compared them to each other, for a lot
of use cases, SQL Alchemy always took the win but had an issue, the async support (which now there
are a few solutions). While doing the research I came across [Encode ORM](https://www.encode.io/orm/).

The creator is the one and only, Tom Chrissie, the same creator of Databases, Django Rest Framework,
Starlette, httpx and a lot more tools used by millions.

There was one issue thou, although ORM was doing a great familiar interface with SQL Alchemy and
providing the async solution needed, it was, by the time of this writting, incomplete and they
even stated that in the documentation and that is how **Saffier** was born.

Saffier uses some of the same concepts of ORM from Encode but rewritten in **Pydantic** but not all,
not even close.

## Saffier

Saffier is some sort of a fork from ORM but rewritten at its core and with a complete set of tools
with a familiar interface to work with. If you are familiar with Django, then you came for a treat 😄.

Saffier leverages the power of **Pyantic** for its fields while offering a friendly, familiar and
easy to use interface.

This ORM was designed to be flexible and compatible with pretty much every ASGI framework, like
[Esmerald](https://esmerald.dymmond.com), Starlette, FastAPI, Sanic, Quart... With simple pluggable
design thanks to its origins.
## Features

While adopting a familiar interface, it offers some cool and powerful features on the top of
SQL Alchemy core.

### Key features

* **Model inheritance** - For those cases where you don't want to repeat yourself while maintaining
intregity of the models.
* **Abstract classes** - That's right! Sometimes you simply want a model that holds common fields
that doesn't need to created as a table in the database.
* **Meta classes** - If you are familiar with Django, this is not new to you and Saffier offers this
in the same fashion.
* **Managers** - Versatility at its core, you can have separate managers for your models to optimise
specific queries and querysets at ease.
* **Filters** - Filter by any field you want and need.
* **Model operators** - Classic operations such as `update`, `get`, `get_or_none`, `bulk_create`,
`bulk_update` and a lot more.
* **Relationships made it easy** - Support for `OneToOne` and `ForeignKey` in the same Django style.
* **Constraints** - Unique constraints through meta fields.

And a lot more you can do here.

## Migrations

Since **Saffier**, like [Encode ORM](https://www.encode.io/orm/), is built on the top of 
[SQLAlchemy core](https://docs.sqlalchemy.org/en/20/core/), you cam use the widely known
[Alembic](https://alembic.sqlalchemy.org/en/latest/) to manage the migrations for you.

## Installation

To install Saffier, simply run:

```shell
$ pip install saffier
```

You can pickup your favourite database driver by yourself or you can run:

**Postgres**

```shell
$ pip install saffier[postgres]
```

**MySQL/MariaDB**

```shell
$ pip install saffier[mysql]
```

**SQLite**

```shell
$ pip install saffier[sqlite]
```

## Quick Start

The following is an example how to start with **Saffier** and more details and examples can be
found throughout the documentation.

**Use** `ipython` **to run the following from the console, since it supports** `await`.

```python
import saffier
from saffier import Database, Registry

database = Database("sqlite:///db.sqlite")
models = Registry(database=database)


class Note(saffier.Model):
    """
    The Note model to be created in the database as a table
    If no name is provided the in Meta class, it will generate
    a "notes" table for you.
    """

    id = saffier.IntegerField(primary_key=True)
    text = saffier.CharField(max_length=255)
    is_completed = saffier.BooleanField(default=False)

    class Meta:
        registry = models


# Create the db and tables
# Don't use this in production! Use Alembic or any tool to manage
# The migrations for you
await models.create_all()

await Note.query.create(text="Buy the stuff.", is_completed=False)

note = await Note.query.get(id=1)
print(note)
# Note(id=1)
```

As stated in the example, if no `tablename` is provided in the `Meta` class, Saffier automatically
generates the name of the table for you by pluralising the class name.

**Exciting!** 

In the documentation we go deeper in explanations and examples, this was just to warm up. 😁
