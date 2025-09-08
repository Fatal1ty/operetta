from typing import TYPE_CHECKING, Annotated, Any, Mapping, TypeVar

from openapify import QueryParam
from openapify.core.openapi.models import Example, ParameterStyle

T = TypeVar("T")
S = TypeVar("S")


if TYPE_CHECKING:
    from typing import Union

    FromBody = Union[T, T]  # noqa: UP007,PYI016
    FromQuery = Union[T, T]  # noqa: UP007,PYI016
    FromPath = Union[T, T]  # noqa: UP007,PYI016
else:

    class FromBody:
        def __init__(
            self,
            media_type: str | None = None,
            required: bool | None = None,
            description: str | None = None,
            example: Any | None = None,
            examples: Mapping[str, Example | Any] | None = None,
        ):
            self.media_type = media_type
            self.required = required
            self.description = description
            self.example = example
            self.examples = examples

        def __class_getitem__(cls, item: T) -> Annotated[T, "FromBody"]:
            return Annotated[item, FromBody()]

    class FromQuery:

        def __init__(
            self,
            name: str | None = None,
            *,
            required: bool | None = None,
            description: str | None = None,
            deprecated: bool | None = None,
            allow_empty_value: bool | None = None,
            style: ParameterStyle | None = None,
            explode: bool | None = None,
            example: Any | None = None,
            examples: Mapping[str, Example | Any] = None,
        ):
            self.query_param = QueryParam(
                required=required,
                description=description,
                deprecated=deprecated,
                allowEmptyValue=allow_empty_value,
                style=style,
                explode=explode,
                example=example,
                examples=examples,
            )
            self.name = name

        def __class_getitem__(cls, item: T) -> Annotated[T, "FromQuery"]:
            return Annotated[item, FromQuery()]

    class FromPath:
        def __init__(
            self,
            name: str | None = None,
            *,
            description: str | None = None,
            example: Any | None = None,
            examples: Mapping[str, Example | Any] = None,
        ):
            self.name = name
            self.description = description
            self.example = example
            self.examples = examples

        def __class_getitem__(cls, item: T) -> Annotated[T, "FromPath"]:
            return Annotated[item, FromPath()]
