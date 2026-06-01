from app.container import AppServices, ServiceContainer


def test_get_instance_is_cached():
    ServiceContainer.reset()
    first = ServiceContainer.get_instance()
    second = ServiceContainer.get_instance()
    assert isinstance(first, AppServices)
    assert first is second


def test_reset_rebuilds_instance():
    first = ServiceContainer.get_instance()
    ServiceContainer.reset()
    assert ServiceContainer.get_instance() is not first
