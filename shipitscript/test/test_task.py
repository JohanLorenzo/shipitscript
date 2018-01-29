import pytest

from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException

from shipitscript.exceptions import TaskVerificationError, BadInstanceConfigurationError
from shipitscript.script import get_default_config
from shipitscript.task import validate_task_schema, get_ship_it_instance_config_from_scope, _get_scope


@pytest.fixture
def context():
    context = Context()
    context.config = get_default_config()
    context.config['ship_it_instances'] = [{
        'api_root': '',
        'timeout_in_seconds': 1,
        'username': 'some-username',
        'password': 'some-password'
    }]
    context.task = {
        'dependencies': ['someTaskId'],
        'payload': {
            'release_name': 'Firefox-59.0b3-build1'
        },
        'scopes': ['project:releng:ship-it:dev'],
    }

    return context


def test_validate_task(context):
    validate_task_schema(context)

    context_with_no_scope = context
    context_with_no_scope.task['scopes'] = []
    with pytest.raises(ScriptWorkerTaskException):
        validate_task_schema(context_with_no_scope)


@pytest.mark.parametrize('api_root, scope, raises', (
    ('http://localhost:5000', 'project:releng:ship-it:dev', False),
    ('http://some-ship-it.url', 'project:releng:ship-it:dev', False),
    ('https://ship-it-dev.allizom.org', 'project:releng:ship-it:staging', False),
    ('https://ship-it-dev.allizom.org/', 'project:releng:ship-it:staging', False),
    ('https://ship-it.mozilla.org', 'project:releng:ship-it:production', False),
    ('https://ship-it.mozilla.org/', 'project:releng:ship-it:production', False),

    ('https://some-ship-it.url', 'project:releng:ship-it:production', True),
    ('https://some-ship-it.url', 'project:releng:ship-it:staging', True),
    # Dev scopes must not reach stage or prod
    ('https://ship-it-dev.allizom.org', 'project:releng:ship-it:dev', True),
    ('https://ship-it.mozilla.org', 'project:releng:ship-it:dev', True),
))
def test_get_ship_it_instance_config_from_scope(context, api_root, scope, raises):
    context.config['ship_it_instances'][0]['api_root'] = api_root
    context.task['scopes'] = [scope]

    if raises:
        with pytest.raises(BadInstanceConfigurationError):
            get_ship_it_instance_config_from_scope(context)
    else:
        assert get_ship_it_instance_config_from_scope(context) == {
            'api_root': api_root,
            'timeout_in_seconds': 1,
            'username': 'some-username',
            'password': 'some-password'
        }


@pytest.mark.parametrize('scopes, raises', (
    (('project:releng:ship-it:dev',), False),
    (('project:releng:ship-it:staging',), False),
    (('project:releng:ship-it:production',), False),
    (('project:releng:ship-it:dev', 'project:releng:ship-it:production',), True),
    (('project:releng:ship-it:unkown_scope',), True),
    (('some:random:scope',), True),
))
def test_get_scope(scopes, raises):
    task = {
        'scopes': scopes
    }

    if raises:
        with pytest.raises(TaskVerificationError):
            _get_scope(task)
    else:
        assert _get_scope(task) == scopes[0]
