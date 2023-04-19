import typing

import sqlalchemy

from saffier.core.schemas import Schema
from saffier.core.utils import ModelUtil
from saffier.db.datastructures import Index, UniqueConstraint
from saffier.db.manager import Manager
from saffier.exceptions import ImproperlyConfigured
from saffier.metaclass import MetaInfo, ModelMeta, ReflectMeta


class Model(ModelMeta, ModelUtil):
    """
    The models will always have an id attribute as primery key.
    The primary key can be whatever desired, from IntegerField, FloatField to UUIDField as long as the `id` field is explicitly declared or else it defaults to BigIntegerField.
    """

    query = Manager()
    _meta = MetaInfo(None)
    _db_model: bool = False
    _raw_query: typing.Optional[str] = None

    def __init__(self, **kwargs: typing.Any) -> None:
        if "pk" in kwargs:
            kwargs[self.pkname] = kwargs.pop("pk")

        for k, v in kwargs.items():
            if k not in self.fields:
                raise ValueError(f"Invalid keyword {k} for class {self.__class__.__name__}")
            setattr(self, k, v)

    class Meta:
        """
        The `Meta` class used to configure each metadata of the model.
        Abstract classes are not generated in the database, instead, they are simply used as
        a reference for field generation.

        Usage:

        .. code-block:: python3

            class User(Model):
                ...

                class Meta:
                    registry = models
                    tablename = "users"

        """

    @property
    def pk(self) -> typing.Any:
        return getattr(self, self.pkname)

    @pk.setter
    def pk(self, value: typing.Any) -> typing.Any:
        setattr(self, self.pkname, value)

    @property
    def raw_query(self) -> typing.Any:
        return getattr(self, self._raw_query)  # type: ignore

    @raw_query.setter
    def raw_query(self, value: typing.Any) -> typing.Any:
        setattr(self, self.raw_query, value)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self}>"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.pkname}={self.pk})"

    @classmethod
    def build_table(cls) -> typing.Any:
        tablename = cls._meta.tablename
        metadata = cls._meta.registry._metadata  # type: ignore
        unique_together = cls._meta.unique_together
        index_constraints = cls._meta.indexes

        columns = []
        for name, field in cls.fields.items():
            columns.append(field.get_column(name))

        # Handle the uniqueness together
        uniques = []
        for field in unique_together or []:
            unique_constraint = cls._get_unique_constraints(field)
            uniques.append(unique_constraint)

        # Handle the indexes
        indexes = []
        for field in index_constraints or []:
            index = cls._get_indexes(field)
            indexes.append(index)

        return sqlalchemy.Table(
            tablename, metadata, *columns, *uniques, *indexes, extend_existing=True
        )

    @classmethod
    def _get_indexes(cls, index: Index) -> typing.Optional[sqlalchemy.Index]:
        """Creates the index based on the Index fields"""
        return sqlalchemy.Index(index.name, *index.fields)

    @classmethod
    def _get_unique_constraints(
        cls, columns: typing.Sequence
    ) -> typing.Optional[sqlalchemy.UniqueConstraint]:
        """
        Returns the unique constraints for the model.

        The columns must be a a list, tuple of strings or a UniqueConstraint object.
        """
        if isinstance(columns, str):
            return sqlalchemy.UniqueConstraint(columns)
        elif isinstance(columns, UniqueConstraint):
            return sqlalchemy.UniqueConstraint(*columns.fields)
        return sqlalchemy.UniqueConstraint(*columns)

    @property
    def table(self) -> sqlalchemy.Table:
        return self.__class__.table

    async def update(self, **kwargs: typing.Any) -> typing.Any:
        fields = {key: field.validator for key, field in self.fields.items() if key in kwargs}
        validator = Schema(fields=fields)
        kwargs = self._update_auto_now_fields(validator.check(kwargs), self.fields)
        pk_column = getattr(self.table.c, self.pkname)
        expression = self.table.update().values(**kwargs).where(pk_column == self.pk)
        await self.database.execute(expression)

        # Update the model instance.
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def delete(self) -> None:
        pk_column = getattr(self.table.c, self.pkname)
        expression = self.table.delete().where(pk_column == self.pk)

        await self.database.execute(expression)

    async def load(self) -> None:
        # Build the select expression.
        pk_column = getattr(self.table.c, self.pkname)
        expression = self.table.select().where(pk_column == self.pk)

        # Perform the fetch.
        row = await self.database.fetch_one(expression)

        # Update the instance.
        for key, value in dict(row._mapping).items():
            setattr(self, key, value)

    @classmethod
    def _from_row(cls, row: typing.Any, select_related: typing.Any = None) -> "Model":
        """
        Instantiate a model instance, given a database row.
        """
        item = {}

        if not select_related:
            select_related = []

        # Instantiate any child instances first.
        for related in select_related:
            if "__" in related:
                first_part, remainder = related.split("__", 1)
                model_cls = cls.fields[first_part].target
                item[first_part] = model_cls._from_row(row, select_related=[remainder])
            else:
                model_cls = cls.fields[related].target
                item[related] = model_cls._from_row(row)

        # Pull out the regular column values.
        for column in cls.table.columns:
            if column.name not in item:
                item[column.name] = row[column]

        return cls(**item)

    def __setattr__(self, key: typing.Any, value: typing.Any) -> typing.Any:
        if key in self.fields:
            # Setting a relationship to a raw pk value should set a
            # fully-fledged relationship instance, with just the pk loaded.
            value = self.fields[key].expand_relationship(value)
        super().__setattr__(key, value)

    def __eq__(self, other: typing.Any) -> bool:
        if self.__class__ != other.__class__:
            return False
        for key in self.fields.keys():
            if getattr(self, key, None) != getattr(other, key, None):
                return False
        return True


class ReflectModel(ReflectMeta, Model):
    """
    Reflect on async engines is not yet supported, therefore, we need to make a sync_engine
    call.
    """

    @classmethod
    def build_table(cls) -> typing.Any:
        metadata = cls._meta.registry._metadata  # type: ignore
        tablename = cls._meta.tablename

        try:
            return sqlalchemy.Table(
                tablename,
                metadata,
                autoload_with=cls._meta.registry.engine.sync_engine,  # type: ignore
            )
        except Exception as e:
            raise ImproperlyConfigured(
                detail=f"Table with the name {tablename} does not exist."
            ) from e
