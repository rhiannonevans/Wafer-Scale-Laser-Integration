# @dataclass

[`@dataclass`](https://docs.python.org/3/library/dataclasses.html)

> Sometimes it is useful to have a data type similar to the Pascal “record” or C “struct”, bundling together a few named data items.

Unlike normal class, it's not convenient to define data class properties as private, as the properties are aimed to be exposed to callers.

The [`frozen`](https://docs.python.org/3/library/dataclasses.html#frozen-instances) parameter can set the data class properties to readonly.
