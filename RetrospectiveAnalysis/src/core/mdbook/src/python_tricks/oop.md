# OOP

Prerequisite: [**Python Class**](https://docs.python.org/3/tutorial/classes.html)

Below are additional tricks uncovered in the prerequisite read.

## @property

[@property](https://docs.python.org/3/library/functions.html#property)

Property is often used with private variables to have a better OOP encapsulation. Use "getter" and "setter" to ensure the validity of the property.

## [Abstract Base Class (ABC)](https://docs.python.org/3/library/abc.html)

Prerequisite: [Interface (OOP)](<https://en.wikipedia.org/wiki/Interface_(object-oriented_programming)>)

A subclass can implement such interfaces defined in the base class by implementing the abstract methods after inheriting from the base class.

The base class can provide a default implementation or not.

### [`@abstractmethod`](https://docs.python.org/3/library/abc.html#abc.abstractmethod)

If the base class has no default implementation, the `@abstractmethod` can enforce the subclass to implement the method.

### [`@staticmethod`](https://docs.python.org/3/library/functions.html#staticmethod)

`@staticmethod` works like a namespace. Static methods neither need to know the class nor an instance. It could be used as an alternative way to initialize a [dataclass](./dataclass.md).

## Example Code

Run the code below and figure out why the error occurs. Open it in an IDE and see the linting.

```python
from abc import ABCMeta, abstractmethod


class Shape(metaclass=ABCMeta):
    @abstractmethod
    def print_info(self):
        ...

    @property
    @abstractmethod
    def area(self) -> float:
        ...

    @staticmethod
    def compare_area(shape1: "Shape", shape2: "Shape"):
        if shape1.area > shape2.area:
            print(
                f"This {shape1.__class__.__name__} is bigger than that {shape2.__class__.__name__}"
            )
        elif shape1.area < shape2.area:
            print(
                f"That {shape2.__class__.__name__} is bigger than this {shape1.__class__.__name__}"
            )
        else:
            print("They are the same size")


class UnknownShape(Shape):
    def __init__(self):
        self.__area = None

    def print_info(self):
        print(f"Unknown Shape with area {self.area}")

    @property
    def area(self):
        return self.__area

    @area.setter
    def area(self, area: float):
        if area < 0:
            raise ValueError("Area cannot be negative")
        else:
            self.__area = area


class Rectangle(Shape):
    def __init__(self, width: float, height: float):
        self.__width = width
        self.__height = height

    def print_info(self):
        print(f"Rectangle: {self.__width} x {self.__height}")

    @property
    def area(self):
        return self.__width * self.__height


class Triangle(Shape):
    def __init__(self, base: float, height: float):
        self.__base = base
        self.__height = height

    def print_info(self):
        print(f"Triangle: {self.__base} x {self.__height}")

    @property
    def area(self):
        return self.__base * self.__height / 2


class Circle(Shape):
    def __init__(self, radius: float):
        self.__radius = radius

    def print_info(self):
        print(f"Circle: {self.__radius}")

    @property
    def area(self):
        return self.__radius * self.__radius * 3.14


if __name__ == "__main__":
    # inheritance demo
    shapes: list[Shape] = [
        Rectangle(2, 3),
        Triangle(3, 4),
        Circle(2),
    ]
    for shape in shapes:
        shape.print_info()
        print(f"Area: {shape.area}")
        # shape.area = 0 # Try uncommenting this line
        # AttributeError: property 'area' of 'Rectangle' object has no setter
        print("------")
    print()

    # static method
    print("-----static method demo-----")
    Shape.compare_area(shapes[0], shapes[1])
    Shape.compare_area(shapes[1], shapes[2])
    print()

    # property setter demo
    print("-----property setter demo-----")
    unknown_shape = UnknownShape()
    if unknown_shape.area is float:
        print("This will not be printed because area is None")
    unknown_shape.print_info()
    unknown_shape.area = 100
    unknown_shape.print_info()

    # validity check by setter:
    unknown_shape.area = -100  # ValueError: Area cannot be negative
    unknown_shape.print_info()

    # abstract class demo
    print("-----abstract class demo-----")
    shape = Shape()  # TypeError: Can't instantiate abstract class...

```
