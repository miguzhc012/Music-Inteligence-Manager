from mim.shared.events import EventBus

def test_event_bus_publish_subscribe():
    bus = EventBus()
    received = []

    def handler(payload):
        received.append(payload)

    bus.subscribe("test_event", handler)
    bus.publish("test_event", "hello")

    assert received == ["hello"]