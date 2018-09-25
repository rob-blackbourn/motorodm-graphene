import inspect
import motorodm
from motorodm.fields import ReferenceField
from motorodm import Document  # , EmbeddedDocument

from collections import OrderedDict


def get_model_fields(model, excluding=None):
    excluding = excluding or []
    attributes = {}
    for attr_name, attr in model._fields.items():
        if attr_name in excluding:
            continue
        attributes[attr_name] = attr
    return OrderedDict(sorted(attributes.items()))


def get_model_reference_fields(model, excluding=None):
    excluding = excluding or []
    attributes = {}
    for attr_name, attr in model._fields.items():
        if attr_name in excluding \
                or not isinstance(attr, ReferenceField):
            continue
        attributes[attr_name] = attr
    return attributes


def is_valid_motorodm_model(model):
    return inspect.isclass(model) and (
        issubclass(model, Document)  # or issubclass(model, EmbeddedDocument)
    )

# noqa


def get_type_for_document(schema, document):
    types = schema.types.values()
    for _type in types:
        type_document = hasattr(_type, '_meta') and getattr(
            _type._meta, 'document', None)
        if document == type_document:
            return _type
