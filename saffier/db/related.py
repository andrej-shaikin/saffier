import functools
from typing import TYPE_CHECKING, Any, Optional, Type, Union

from saffier import fields

if TYPE_CHECKING:
    from saffier import Model, ReflectModel


class RelatedField:
    """
    When a `related_name` is generated, creates a RelatedField from the table pointed
    from the ForeignKey declaration and the the table declaring it.
    """

    def __init__(
        self,
        related_name: str,
        related_to: Union[Type["Model"], Type["ReflectModel"]],
        related_from: Optional[Union[Type["Model"], Type["ReflectModel"]]] = None,
        instance: Optional[Union[Type["Model"], Type["ReflectModel"]]] = None,
    ) -> None:
        self.related_name = related_name
        self.related_to = related_to
        self.related_from = related_from
        self.instance = instance

    def __get__(self, instance: Any, owner: Any) -> Any:
        return self.__class__(
            related_name=self.related_name,
            related_to=self.related_to,
            instance=instance,
            related_from=self.related_from,
        )

    def __getattr__(self, item: Any) -> Any:
        """
        Gets the attribute from the queryset and if it does not
        exist, then lookup in the model.
        """
        manager = self.related_from._meta.manager
        try:
            attr = getattr(manager.get_queryset(), item)
        except AttributeError:
            attr = getattr(self.related_from, item)

        func = self.wrap_args(attr)
        return func

    def get_foreign_key_field_name(self) -> str:
        """
        Table lookup for the given field containing the related field.
        """
        field_name: str = None

        for field, value in self.related_from.fields.items():
            if isinstance(value, (fields.ForeignKey, fields.OneToOneField)):
                if value.related_name == self.related_name:
                    field_name = field
                    break
        return field_name

    def wrap_args(self, func: Any) -> Any:
        @functools.wraps(func)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            field = self.get_foreign_key_field_name()
            kwargs[field] = self.instance.pk
            return func(*args, **kwargs)

        return wrapped

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self}>"

    def __str__(self) -> str:
        return f"({self.related_to.__name__}={self.related_name})"
