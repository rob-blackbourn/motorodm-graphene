class Registry(object):

    def __init__(self):
        self._registry = {}

    def register(self, cls):
        from .types import MotorOdmObjectType
        assert issubclass(
            cls, MotorOdmObjectType), 'Only MotorOdmObjectTypes can be registered, received "{}"'.format(
            cls.__name__)
        assert cls._meta.registry == self, 'Registry for a Model have to match.'
        self._registry[cls._meta.model] = cls

        # Rescan all fields
        for model, klass in self._registry.items():
            klass.rescan_fields()

    def get_type_for_model(self, model):
        return self._registry.get(model)


registry = None


def get_global_registry():
    global registry
    if not registry:
        registry = Registry()
    return registry


def reset_global_registry():
    global registry
    registry = None
