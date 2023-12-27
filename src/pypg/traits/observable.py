from __future__ import annotations

__all__ = [
    "DeliveryPolicy",
    "AsynchronousDelivery",
    "SynchronousDelivery",
    "Subscription",
    "Observable",
    "OnChange",
    "Always",
    "watch",
]
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable
from threading import Event, Lock, Thread
from typing import Any

from pypg import Property, PropertyClass
from pypg.property import DataModifierMixin
from pypg.type_utils import get_fully_qualified_name


class DeliveryPolicy(ABC):
    def __init__(
        self, on_update: Callable[[Any], Any], update_policy: UpdatePolicy
    ):
        self._on_update = on_update
        self._update_policy = update_policy

    @abstractmethod
    def update(self, value):
        """Process a datum for distribution to watchers."""

    @abstractmethod
    def cancel(self):
        """Implement behavior to discontinue delivery."""


class SynchronousDelivery(DeliveryPolicy):
    def cancel(self):
        """no cancellation required."""

    def update(self, value):
        if self._update_policy.requires_update(value):
            self._on_update(value)


class AsynchronousDelivery(DeliveryPolicy):
    def cancel(self):
        self._canceled = True

    def update(self, value):
        self._data_queue.append(value)
        with self._data_lock:
            self._queue_empty_event.clear()
            if not self._delivery_thread:
                self._delivery_thread = Thread(target=self._deliver_queue, daemon=True)
                self._delivery_thread.start()

    def await_delivery(self, timeout: float | None = None):
        return self._queue_empty_event.wait(timeout)

    def _deliver_queue(self):
        while not self._canceled:
            try:
                value = self._data_queue.popleft()
                if self._update_policy.requires_update(value):
                    try:
                        self._on_update(value)
                    except Exception as e:
                        self._on_error(value, e)
            except IndexError:
                with self._data_lock:
                    if self._data_queue:  # pragma: no cover
                        continue
                    self._queue_empty_event.set()
                    self._delivery_thread = None
                    return

    def __init__(
        self,
        on_update: Callable[[Any], Any],
        update_policy: UpdatePolicy,
        on_error: Callable[[Any, Exception], Any] = print,
    ):
        super().__init__(on_update, update_policy)
        self._canceled = False
        self._data_lock = Lock()
        self._on_error = on_error
        self._data_queue = deque()
        self._delivery_thread = None
        self._queue_empty_event = Event()


class UpdatePolicy(ABC):
    @abstractmethod
    def requires_update(self, value) -> bool:
        """determines whether a given value requires an update to be broadcast to observers."""


class Always(UpdatePolicy):
    def requires_update(self, value):
        return True


class OnChange(UpdatePolicy):
    _UNCHANGED = object()
    _last = _UNCHANGED

    def requires_update(self, value):
        result = value != self._last
        self._last = value
        return result


class Observable(DataModifierMixin, ABC):
    def __init_instance__(self, instance: PropertyClass, _):
        setattr(instance, self.watchlist_key(self.subject), [])

    @classmethod
    def watchlist_key(cls, p: Property):
        return f"__{p.name}_Observable__watchlist"

    @classmethod
    def get_watchlist(cls, instance: PropertyClass, p: Property):
        return getattr(instance, cls.watchlist_key(p))

    def apply(self, instance, value) -> Any:
        watchlist: list[DeliveryPolicy] = self.get_watchlist(
            instance, self.subject
        )
        for udp in watchlist:
            udp.update(value)
        return value

    @classmethod
    def watch(
        cls,
        instance: PropertyClass,
        p: Property | str,
        delivery_policy: DeliveryPolicy,
    ) -> Subscription:
        if isinstance(p, str):
            p: Property = getattr(type(instance), p)
        watchlist = cls.get_watchlist(instance, p)
        watchlist.append(delivery_policy)
        return Subscription(delivery_policy, watchlist)

    def __str__(self):
        return str([get_fully_qualified_name(t) for t in self.modifier_triggers])

class Subscription:
    def __init__(
        self, delivery_policy: DeliveryPolicy, watchlist: list[DeliveryPolicy]
    ):
        self._delivery_policy = delivery_policy
        self._watchlist = watchlist

    def cancel(self):
        try:
            self._watchlist.remove(self._delivery_policy)
        except ValueError:
            pass
        self._delivery_policy.cancel()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cancel()


watch = Observable.watch
