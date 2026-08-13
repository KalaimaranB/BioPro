# Central Event Bus Architecture

The `EventBus` is Karcytics's thread-safe publish/subscribe broker used for decoupled communication between UI components, plugins, and background workers.

## Design goals

- Low-latency message delivery across threads
- Simple API for publishers and subscribers
- Message ordering guarantees per topic
- Ability to queue events when handlers are busy

## API (conceptual)

```py
class EventBus:
    def publish(topic: str, data: Any = None) -> None: ...
    def subscribe(topic: str, callback: Callable[[Any], None]) -> Callable: ...
    def unsubscribe(topic: str, callback: Callable[[Any], None]) -> None: ...
```

## Threading model

- Publishers can be any thread; the bus enqueues messages onto a dispatch queue.
- A worker thread (or Qt main thread via posted events) dequeues messages and calls subscribers.
- Handlers that perform long computations MUST offload to `AnalysisWorker` or other thread pools.

## Example usage

```py
def on_analysis_finished(result):
    # run in main thread: update UI
    ui_widget.display(result)


EventBus.subscribe("analysis.finished", on_analysis_finished)
EventBus.publish("analysis.finished", {"success": True, "data": ...})
```

## Best practices

- Use small payloads in events (IDs or lightweight dicts) and fetch heavy blobs via shared caches.
- Prefer namespaced topic names: `plugin.<plugin_id>.event_name`.
- Ensure `unsubscribe()` is called in `cleanup()` to avoid dangling callbacks.

## Links

- Source: `karcytics/core/event_bus.py`
