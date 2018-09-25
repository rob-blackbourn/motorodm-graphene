from collections import OrderedDict

from graphene import Field
from graphene.relay import Connection, Node
from graphene.types.objecttype import ObjectType, ObjectTypeOptions
from graphene.types.utils import yank_fields_from_attrs
from motorodm import ListField

from motorodm.graphene.converter import convert_motorodm_field
from motorodm.graphene.registry import Registry, get_global_registry
from motorodm.graphene.utils import (
    get_model_fields, is_valid_motorodm_model)


def construct_fields(model, registry, only_fields, exclude_fields):
    _model_fields = get_model_fields(model)
    fields = OrderedDict()
    self_referenced = OrderedDict()
    for name, field in _model_fields.items():
        is_not_in_only = only_fields and name not in only_fields
        is_excluded = name in exclude_fields
        if is_not_in_only or is_excluded:
            # We skip this field if we specify only_fields and is not
            # in there. Or when we exclude this field in exclude_fields
            continue
        if isinstance(field, ListField):
            # Take care of list of self-reference.
            document_type_obj = field.field.__dict__.get(
                'document_type_obj', None)
            if document_type_obj == model._class_name \
                    or isinstance(document_type_obj, model) \
                    or document_type_obj == model:
                self_referenced[name] = field
                continue
        # pylint: disable=assignment-from-no-return
        converted = convert_motorodm_field(field, registry)
        if not converted:
            continue
        fields[name] = converted

    return fields, self_referenced


def construct_self_referenced_fields(self_referenced, registry):
    fields = OrderedDict()
    for name, field in self_referenced.items():
        # pylint: disable=assignment-from-no-return
        converted = convert_motorodm_field(field, registry)
        if not converted:
            continue
        fields[name] = converted

    return fields


class MotorOdmObjectTypeOptions(ObjectTypeOptions):

    model = None  # type: Model
    registry = None  # type: Registry
    connection = None  # type: Type[Connection]
    filter_fields = ()


class MotorOdmObjectType(ObjectType):

    @classmethod
    def __init_subclass_with_meta__(cls, model=None, registry=None, skip_registry=False,
                                    only_fields=(), exclude_fields=(), filter_fields=None, connection=None,
                                    connection_class=None, use_connection=None, interfaces=(), **options):

        assert is_valid_motorodm_model(model), (
            'You need to pass a valid MotorOdm Model in {}.Meta, received "{}".'
        ).format(cls.__name__, model)

        if not registry:
            registry = get_global_registry()

        assert isinstance(registry, Registry), (
            'The attribute registry in {} needs to be an instance of '
            'Registry, received "{}".'
        ).format(cls.__name__, registry)

        converted_fields, self_referenced = construct_fields(
            model, registry, only_fields, exclude_fields
        )
        motorodm_fields = yank_fields_from_attrs(
            converted_fields, _as=Field)
        if use_connection is None and interfaces:
            use_connection = any((issubclass(interface, Node)
                                  for interface in interfaces))

        if use_connection and not connection:
            # We create the connection automatically
            if not connection_class:
                connection_class = Connection

            connection = connection_class.create_type(
                '{}Connection'.format(cls.__name__), node=cls)

        if connection is not None:
            assert issubclass(connection, Connection), (
                'The connection must be a Connection. Received {}'
            ).format(connection.__name__)

        _meta = MotorOdmObjectTypeOptions(cls)
        _meta.model = model
        _meta.registry = registry
        _meta.fields = motorodm_fields
        _meta.filter_fields = filter_fields
        _meta.connection = connection
        # Save them for later
        _meta.only_fields = only_fields
        _meta.exclude_fields = exclude_fields

        super(MotorOdmObjectType, cls).__init_subclass_with_meta__(
            _meta=_meta, interfaces=interfaces, **options
        )

        if not skip_registry:
            registry.register(cls)
            # Notes: Take care list of self-reference fields.
            converted_fields = construct_self_referenced_fields(
                self_referenced, registry)
            if converted_fields:
                motorodm_fields = yank_fields_from_attrs(
                    converted_fields, _as=Field)
                cls._meta.fields.update(motorodm_fields)
                registry.register(cls)

    @classmethod
    def rescan_fields(cls):
        """Attempts to rescan fields and will insert any not converted initially"""

        converted_fields, self_referenced = construct_fields(
            cls._meta.model, cls._meta.registry,
            cls._meta.only_fields, cls._meta.exclude_fields
        )

        motorodm_fields = yank_fields_from_attrs(
            converted_fields, _as=Field)

        # The initial scan should take precidence
        for field in motorodm_fields:
            if field not in cls._meta.fields:
                cls._meta.fields.update({field: motorodm_fields[field]})
        # Self-referenced fields can't change between scans!

    # noqa

    @classmethod
    def is_type_of(cls, root, info):
        if isinstance(root, cls):
            return True
        if not is_valid_motorodm_model(type(root)):
            raise Exception((
                'Received incompatible instance "{}".'
            ).format(root))
        return isinstance(root, cls._meta.model)

    @classmethod
    def get_node(cls, info, id):
        return cls._meta.model.objects.get(pk=id)

    def resolve_id(self, info):
        # pylint: disable=no-member
        return str(self._identity)

    # @classmethod
    # def get_connection(cls):
    #     return connection_for_type(cls)
