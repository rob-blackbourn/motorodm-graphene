from functools import singledispatch
import graphene
from graphene.types.json import JSONString
import motorodm
from .fields import MotorOdmConnectionField


@singledispatch
def convert_motorodm_field(field, registry=None):
    raise Exception(
        "Don't know how to convert the MotorOdm field %s (%s)" %
        (field, field.__class__))


@convert_motorodm_field.register(motorodm.StringField)
def convert_field_to_string(field, registry=None):
    return graphene.String(description=field.db_name, required=field.required)


@convert_motorodm_field.register(motorodm.ObjectIdField)
def convert_field_to_id(field, registry=None):
    return graphene.ID(description=field.db_name, required=field.required)


@convert_motorodm_field.register(motorodm.IntField)
def convert_field_to_int(field, registry=None):
    return graphene.Int(description=field.db_name, required=field.required)


@convert_motorodm_field.register(motorodm.BooleanField)
def convert_field_to_boolean(field, registry=None):
    return graphene.NonNull(graphene.Boolean, description=field.db_name)


@convert_motorodm_field.register(motorodm.DecimalField)
@convert_motorodm_field.register(motorodm.fields.FloatField)
def convert_field_to_float(field, registry=None):
    return graphene.Float(description=field.db_name, required=field.required)


@convert_motorodm_field.register(motorodm.fields.JsonField)
def convert_dict_to_jsonstring(field, registry=None):
    return graphene.JSONString(description=field.db_name, required=field.required)


@convert_motorodm_field.register(motorodm.DateTimeField)
def convert_date_to_string(field, registry=None):
    return graphene.String(description=field.db_name, required=field.required)


@convert_motorodm_field.register(motorodm.ListField)
def convert_field_to_list(field, registry=None):
    # pylint: disable=assignment-from-no-return
    base_type = convert_motorodm_field(field.field, registry=registry)
    if isinstance(base_type, (graphene.Dynamic)):
        base_type = base_type.get_type()
        if base_type is None:
            return
        base_type = base_type._type

    if graphene.is_node(base_type):
        return MotorOdmConnectionField(base_type)

    # Non-relationship field
    relations = (motorodm.fields.ReferenceField,
                 motorodm.fields.EmbeddedDocumentField)
    if not isinstance(base_type, (graphene.List, graphene.NonNull)) \
            and not isinstance(field.field, relations):
        base_type = type(base_type)

    return graphene.List(base_type, description=field.db_name, required=field.required)


@convert_motorodm_field.register(motorodm.EmbeddedDocumentField)
@convert_motorodm_field.register(motorodm.ReferenceField)
def convert_field_to_dynamic(field, registry=None):
    model = field.document_type

    def dynamic_type():
        _type = registry.get_type_for_model(model)
        if not _type:
            return None
        return graphene.Field(_type)

    return graphene.Dynamic(dynamic_type)
