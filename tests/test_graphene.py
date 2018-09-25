import pytest

import asyncio
from motorodm import Document, StringField, ObjectIdField
import graphene
from graphql.execution.executors.asyncio import AsyncioExecutor
from motorodm.graphene import MotorOdmObjectType
from motor.motor_asyncio import AsyncIOMotorClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_smoke():
    client = AsyncIOMotorClient()

    class UserModel(Document):
        __collection__ = 'user'
        email = StringField(required=True, unique=True)
        first_name = StringField(db_name='firstName')
        last_name = StringField(db_name='lastName')

    db = client.test_motorodm

    await UserModel.qs(db).drop()
    await UserModel.qs(db).ensure_indices()

    await UserModel(email='rob@example.com', first_name='Rob', last_name='Blackbourn').qs(db).save()
    await UserModel(email='ann-marie@example.com', first_name='Ann-Marie', last_name='Dutton').qs(db).save()

    class User(MotorOdmObjectType):
        class Meta:
            model = UserModel

    class CreateUser(graphene.Mutation):

        Output = User

        class Arguments:
            email = graphene.String(required=True)
            first_name = graphene.String(required=True)
            last_name = graphene.String(required=True)

        async def mutate(self, info, **kwargs):
            user = await UserModel(**kwargs).qs(info.context['db']).save()
            return user

    class Query(graphene.ObjectType):
        users = graphene.List(User)
        user = graphene.Field(
            User, email=graphene.String(), id=graphene.ID())

        async def resolve_users(self, info, email=None):
            cursor = UserModel.qs(info.context['db']).find()
            # return await cursor.to_list(100)
            return [user async for user in cursor]

        async def resolve_user(self, info, **kwargs):
            return await UserModel.qs(info.context['db']).find_one(**kwargs)

    class Mutation(graphene.ObjectType):
        create_user = CreateUser.Field()

    schema = graphene.Schema(query=Query, mutation=Mutation)

    result = await schema.execute(
        '''query {
            users {
                id,
                firstName,
                lastName
            }
        }''',
        context={'db': db},
        executor=AsyncioExecutor(),
        return_promise=True)
    assert result.errors is None, "The query should have no errors"
    assert 1 == len(result.data), "The data should contain a single result set"
    assert 'users' in result.data, "The data should contain the 'users' result set"
    assert 2 == len(result.data['users']
                    ), "There should be two users in the result set"

    result = await schema.execute(
        '''mutation testMutation {
            createUser(email: "john.doe@example.com", firstName: "John", lastName: "Doe") {
                id
                email
                firstName
                lastName
            }
        }''',
        context={'db': db},
        executor=AsyncioExecutor(),
        return_promise=True)
    assert result.errors is None, "The mutation should have no errors"
    assert 1 == len(result.data), "The mutation should have one result set"
    assert 'createUser' in result.data, "The data should contain the result field"
    assert 4 == len(result.data['createUser']
                    ), "The result set should have four fields"
    assert "john.doe@example.com" == result.data['createUser'][
        'email'], "The email should match the input data"
    assert 'John' == result.data['createUser']['firstName'], "The first name should match the input data"
    assert 'Doe' == result.data['createUser']['lastName'], "The last name should match the input data"

    id = result.data['createUser']['id']
    email = result.data['createUser']['email']

    result = await schema.execute(
        '''query {
            user(email: "rob@example.com") {
                id
                email
                firstName
                lastName
            }
        }''',
        context={'db': db},
        executor=AsyncioExecutor(),
        return_promise=True)
    assert result.errors is None, "The query should have no errors"
    assert 1 == len(result.data), "The query should return one result set"
    assert 4 == len(result.data['user']
                    ), "The result set should have four fields"
    assert 'id' in result.data['user'], "The 'id' field should be a returned field"
    assert 'email' in result.data['user'], "The 'email' field should be a returned field"
    assert 'firstName' in result.data['user'], "The 'firstName' field should be a returned field"
    assert 'lastName' in result.data['user'], "The 'lastName' field should be a returned field"

    result = await schema.execute(
        '''query getUser($email: String!) {
            user(email: $email) {
                id
                firstName
                lastName
            }
        }''',
        context={'db': db},
        executor=AsyncioExecutor(),
        return_promise=True,
        variables={'email': email})
    assert result.errors is None, "A query with variables should return have no errors"
    assert 1 == len(result.data), "The query should have one result"
    assert 3 == len(result.data['user']), "The result should have three fields"
    assert id == result.data['user']['id'], "The id should corresepond to the mutated user"

    result = await schema.execute(
        '''query getUser($id: ID!) {
            user(id: $id) {
                email
            }
        }''',
        context={'db': db},
        executor=AsyncioExecutor(),
        return_promise=True,
        variables={'id': id})
    assert result.errors is None, "A query with variables should have no errors"
    assert 1 == len(
        result.data['user']), "A query with variables should return a single data value"
    assert email == result.data['user']['email'], "The result should have the correct id"

    await UserModel.qs(db).drop()
