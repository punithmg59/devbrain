"""
Dependency Injection Contracts for Graph Query Engine.
"""

from typing import Any, Protocol, Type, TypeVar

T = TypeVar("T")


class ComponentProvider(Protocol):
    """
    Contract for retrieving resolved component instances by interface type.
    """

    def get_component(self, interface_type: Type[T]) -> T:
        """
        Retrieves an instance implementing the specified interface type.
        """
        ...

    def has_component(self, interface_type: Type[Any]) -> bool:
        """
        Checks if a component implementation is registered.
        """
        ...


class ComponentFactory(Protocol):
    """
    Contract for instantiating component instances.
    """

    def create_component(
        self,
        component_type: Type[T],
        **parameters: Any,
    ) -> T:
        """
        Factory method for manufacturing a component instance with parameter overrides.
        """
        ...


class ServiceRegistry(Protocol):
    """
    Contract for registering service mappings and providers into DI container.
    """

    def register(
        self,
        interface_type: Type[T],
        implementation: Type[T] | T,
        singleton: bool = True,
    ) -> None:
        """
        Registers an implementation class or instance for an interface.
        """
        ...

    def resolve(self, interface_type: Type[T]) -> T:
        """
        Resolves the singleton or transient instance for the interface type.
        """
        ...

    def has_service(self, interface_type: Type[Any]) -> bool:
        """
        Checks if a service is registered.
        """
        ...


class Disposable(Protocol):
    """
    Contract for resources requiring explicit teardown or release.
    """

    def dispose(self) -> None:
        """
        Releases underlying unmanaged or managed resources.
        """
        ...
