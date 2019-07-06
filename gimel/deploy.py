from __future__ import print_function
from botocore.client import ClientError
import os
import redis
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
try:
    from gimel import logger
    from gimel.gimel import _redis
    from gimel.config import config
    from gimel.aws_api import iam, apigateway, aws_lambda, region, check_aws_credentials
except ImportError:
    import logger
    from gimel import _redis
    from config import config
    from aws_api import iam, apigateway, aws_lambda, region, check_aws_credentials


logger = logger.setup()
LIVE = 'live'
REVISIONS = 5
TRACK_ENDPOINT = 'track'
EXPERIMENTS_ENDPOINT = 'experiments'
POLICY = """{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": [
                "*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "kinesis:GetRecords",
                "kinesis:GetShardIterator",
                "kinesis:DescribeStream",
                "kinesis:ListStreams",
                "kinesis:PutRecord",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        }
    ]
}"""
ASSUMED_ROLE_POLICY = """{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            }
        },
        {
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {
                "Service": "apigateway.amazonaws.com"
            }
        }
    ]
}"""
# source: https://aws.amazon.com/blogs/compute/using-api-gateway-mapping-templates-to-handle-changes-in-your-back-end-apis/  # noqa
REQUEST_TEMPLATE = {'application/json':
    """{
        #set($queryMap = $input.params().querystring)
        #foreach($key in $queryMap.keySet())
            "$key" : "$queryMap.get($key)"
            #if($foreach.hasNext),#end
        #end
       }
    """}

WIRING = [
    {
        "lambda": {
            "FunctionName": "gimel-track",
            "Handler": "gimel.track",
            "MemorySize": 128,
            "Timeout": 3
        },
        "api_gateway": {
            "pathPart": TRACK_ENDPOINT,
            "method": {
                "httpMethod": "GET",
                "apiKeyRequired": False,
                "requestParameters": {
                    "method.request.querystring.namespace": False,
                    "method.request.querystring.experiment": False,
                    "method.request.querystring.variant": False,
                    "method.request.querystring.event": False,
                    "method.request.querystring.uuid": False
                }
            }
        }
    },
    {
        "lambda": {
            "FunctionName": "gimel-all-experiments",
            "Handler": "gimel.all",
            "MemorySize": 128,
            "Timeout": 60
        },
        "api_gateway": {
            "pathPart": EXPERIMENTS_ENDPOINT,
            "method": {
                "httpMethod": "GET",
                "apiKeyRequired": True,
                "requestParameters": {
                    "method.request.querystring.namespace": False,
                    "method.request.querystring.scope": False
                }
            }
        }
    },
    {
        "lambda": {
            "FunctionName": "gimel-delete-experiment",
            "Handler": "gimel.delete",
            "MemorySize": 128,
            "Timeout": 30
        },
        "api_gateway": {
            "pathPart": "delete",
            "method": {
                "httpMethod": "DELETE",
                "apiKeyRequired": True,
                "requestParameters": {
                    "method.request.querystring.namespace": False,
                    "method.request.querystring.experiment": False,
                }
            }
        }
    }
]


def prepare_zip():
    from pkg_resources import resource_filename as resource
    from json import dumps
    logger.info('creating/updating gimel.zip')
    with ZipFile('gimel.zip', 'w', ZIP_DEFLATED) as zipf:
        info = ZipInfo('config.json')
        info.external_attr = 0o664 << 16
        zipf.writestr(info, dumps(config))
        zipf.write(resource('gimel', 'config.py'), 'config.py')
        zipf.write(resource('gimel', 'gimel.py'), 'gimel.py')
        zipf.write(resource('gimel', 'logger.py'), 'logger.py')
        for root, dirs, files in os.walk(resource('gimel', 'vendor')):
            for file in files:
                real_file = os.path.join(root, file)
                relative_file = os.path.relpath(real_file,
                                                resource('gimel', ''))
                zipf.write(real_file, relative_file)


def role():
    new_role = False
    try:
        logger.info('finding role')
        iam('get_role', RoleName='gimel')
    except ClientError:
        logger.info('role not found. creating')
        iam('create_role', RoleName='gimel',
            AssumeRolePolicyDocument=ASSUMED_ROLE_POLICY)
        new_role = True

    role_arn = iam('get_role', RoleName='gimel', query='Role.Arn')
    logger.debug('role_arn={}'.format(role_arn))

    logger.info('updating role policy')

    iam('put_role_policy', RoleName='gimel', PolicyName='gimel',
        PolicyDocument=POLICY)

    if new_role:
        from time import sleep
        logger.info('waiting for role policy propagation')
        sleep(5)

    return role_arn


def _cleanup_old_versions(name):
    logger.info('cleaning up old versions of {0}. Keeping {1}'.format(
        name, REVISIONS))
    versions = _versions(name)
    for version in versions[0:(len(versions) - REVISIONS)]:
        logger.debug('deleting {} version {}'.format(name, version))
        aws_lambda('delete_function',
                   FunctionName=name,
                   Qualifier=version)


def _function_alias(name, version, alias=LIVE):
    try:
        logger.info('creating function alias {0} for {1}:{2}'.format(
            alias, name, version))
        arn = aws_lambda('create_alias',
                         FunctionName=name,
                         FunctionVersion=version,
                         Name=alias,
                         query='AliasArn')
    except ClientError:
        logger.info('alias {0} exists. updating {0} -> {1}:{2}'.format(
            alias, name, version))
        arn = aws_lambda('update_alias',
                         FunctionName=name,
                         FunctionVersion=version,
                         Name=alias,
                         query='AliasArn')
    return arn


def _versions(name):
    versions = aws_lambda('list_versions_by_function',
                          FunctionName=name,
                          query='Versions[].Version')
    return versions[1:]


def _get_version(name, alias=LIVE):
    return aws_lambda('get_alias',
                      FunctionName=name,
                      Name=alias,
                      query='FunctionVersion')


def rollback_lambda(name, alias=LIVE):
    all_versions = _versions(name)
    live_version = _get_version(name, alias)
    try:
        live_index = all_versions.index(live_version)
        if live_index < 1:
            raise RuntimeError('Cannot find previous version')
        prev_version = all_versions[live_index - 1]
        logger.info('rolling back to version {}'.format(prev_version))
        _function_alias(name, prev_version)
    except RuntimeError as error:
        logger.error('Unable to rollback. {}'.format(repr(error)))


def rollback(alias=LIVE):
    for lambda_function in ('gimel-track', 'gimel-all-experiments'):
        rollback_lambda(lambda_function, alias)


def get_create_api():
    api_id = apigateway('get_rest_apis',
                        query='items[?name==`gimel`] | [0].id')
    if not api_id:
        api_id = apigateway('create_rest_api', name='gimel',
                            description='Gimel API', query='id')
    logger.debug("api_id={}".format(api_id))
    return api_id


def get_api_key():
    return apigateway('get_api_keys',
                      query='items[?name==`gimel`] | [0].id')


def api_key(api_id):
    key = get_api_key()
    if key:
        apigateway('update_api_key', apiKey=key,
                   patchOperations=[{'op': 'add', 'path': '/stages',
                                     'value': '{}/prod'.format(api_id)}])
    else:
        key = apigateway('create_api_key', name='gimel', enabled=True,
                         stageKeys=[{'restApiId': api_id, 'stageName': 'prod'}])
    return key


def resource(api_id, path):
    resource_id = apigateway('get_resources', restApiId=api_id,
                             query='items[?path==`/{}`].id | [0]'.format(path))
    if resource_id:
        return resource_id
    root_resource_id = apigateway('get_resources', restApiId=api_id,
                                  query='items[?path==`/`].id | [0]')
    resource_id = apigateway('create_resource', restApiId=api_id,
                             parentId=root_resource_id,
                             pathPart=path, query='id')
    return resource_id


def function_uri(function_arn, region):
    uri = ('arn:aws:apigateway:{0}:lambda:path/2015-03-31/functions'
          '/{1}/invocations').format(region, function_arn)
    logger.debug("uri={0}".format(uri))
    return uri


def _clear_method(api_id, resource_id, http_method):
    try:
        method = apigateway('get_method', restApiId=api_id,
                            resourceId=resource_id,
                            httpMethod=http_method)
    except ClientError:
        method = None
    if method:
        apigateway('delete_method', restApiId=api_id, resourceId=resource_id,
                   httpMethod=http_method)


def cors(api_id, resource_id):
    _clear_method(api_id, resource_id, 'OPTIONS')
    apigateway('put_method', restApiId=api_id, resourceId=resource_id,
               httpMethod='OPTIONS', authorizationType='NONE',
               apiKeyRequired=False)
    apigateway('put_integration', restApiId=api_id, resourceId=resource_id,
               httpMethod='OPTIONS', type='MOCK', integrationHttpMethod='POST',
               requestTemplates={'application/json': '{"statusCode": 200}'})
    apigateway('put_method_response', restApiId=api_id, resourceId=resource_id,
               httpMethod='OPTIONS', statusCode='200',
               responseParameters={
                   "method.response.header.Access-Control-Allow-Origin": False,
                   "method.response.header.Access-Control-Allow-Methods": False,
                   "method.response.header.Access-Control-Allow-Headers": False},
               responseModels={'application/json': 'Empty'})
    apigateway('put_integration_response', restApiId=api_id,
               resourceId=resource_id, httpMethod='OPTIONS', statusCode='200',
               responseParameters={
                   "method.response.header.Access-Control-Allow-Origin": "'*'",
                   "method.response.header.Access-Control-Allow-Methods": "'GET,OPTIONS'",
                   "method.response.header.Access-Control-Allow-Headers": "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"},  # noqa
               responseTemplates={'application/json': ''})


def deploy_api(api_id):
    logger.info('deploying API')
    return apigateway('create_deployment', restApiId=api_id,
                      description='gimel deployment',
                      stageName='prod',
                      stageDescription='gimel production',
                      cacheClusterEnabled=False,
                      query='id')


def api_method(api_id, resource_id, role_arn, function_uri, wiring):
    http_method = wiring['method']['httpMethod']
    _clear_method(api_id, resource_id, http_method)
    apigateway('put_method', restApiId=api_id, resourceId=resource_id,
               authorizationType='NONE',
               **wiring['method'])
    apigateway('put_integration', restApiId=api_id, resourceId=resource_id,
               httpMethod=http_method, type='AWS', integrationHttpMethod='POST',
               credentials=role_arn,
               uri=function_uri,
               requestTemplates=REQUEST_TEMPLATE)
    apigateway('put_method_response', restApiId=api_id, resourceId=resource_id,
               httpMethod=http_method, statusCode='200',
               responseParameters={
                   "method.response.header.Access-Control-Allow-Origin": False,
                   "method.response.header.Pragma": False,
                   "method.response.header.Cache-Control": False},
               responseModels={'application/json': 'Empty'})
    apigateway('put_integration_response', restApiId=api_id,
               resourceId=resource_id, httpMethod=http_method, statusCode='200',
               responseParameters={
                   "method.response.header.Access-Control-Allow-Origin": "'*'",
                   "method.response.header.Pragma": "'no-cache'",
                   "method.response.header.Cache-Control": "'no-cache, no-store, must-revalidate'"},
               responseTemplates={'application/json': ''})


def create_update_lambda(role_arn, wiring):
    name, handler, memory, timeout = (wiring[k] for k in ('FunctionName',
                                                          'Handler',
                                                          'MemorySize',
                                                          'Timeout'))
    try:
        logger.info('finding lambda function')
        function_arn = aws_lambda('get_function',
                                  FunctionName=name,
                                  query='Configuration.FunctionArn')
    except ClientError:
        function_arn = None
    if not function_arn:
        logger.info('creating new lambda function {}'.format(name))
        with open('gimel.zip', 'rb') as zf:
            function_arn, version = aws_lambda('create_function',
                                               FunctionName=name,
                                               Runtime='python2.7',
                                               Role=role_arn,
                                               Handler=handler,
                                               MemorySize=memory,
                                               Timeout=timeout,
                                               Publish=True,
                                               Code={'ZipFile': zf.read()},
                                               query='[FunctionArn, Version]')
    else:
        logger.info('updating lambda function {}'.format(name))
        aws_lambda('update_function_configuration',
                   FunctionName=name,
                   Runtime='python2.7',
                   Role=role_arn,
                   Handler=handler,
                   MemorySize=memory,
                   Timeout=timeout)
        with open('gimel.zip', 'rb') as zf:
            function_arn, version = aws_lambda('update_function_code',
                                               FunctionName=name,
                                               Publish=True,
                                               ZipFile=zf.read(),
                                               query='[FunctionArn, Version]')
    function_arn = _function_alias(name, version)
    _cleanup_old_versions(name)
    logger.debug('function_arn={} ; version={}'.format(function_arn, version))
    return function_arn


def create_update_api(role_arn, function_arn, wiring):
    logger.info('creating or updating api /{}'.format(wiring['pathPart']))
    api_id = get_create_api()
    resource_id = resource(api_id, wiring['pathPart'])
    uri = function_uri(function_arn, region())
    api_method(api_id, resource_id, role_arn, uri, wiring)
    cors(api_id, resource_id)


def js_code_snippet():
    api_id = get_create_api()
    api_region = region()
    endpoint = TRACK_ENDPOINT
    logger.info('AlephBet JS code snippet:')
    logger.info(
        """

        <!-- Copy and paste this snippet to start tracking with gimel -->

        <script src="https://unpkg.com/alephbet/dist/alephbet.min.js"></script>
        <script>

        // * javascript code snippet to track experiments with AlephBet *
        // * For more information: https://github.com/Alephbet/alephbet *

        track_url = 'https://%(api_id)s.execute-api.%(api_region)s.amazonaws.com/prod/%(endpoint)s';
        namespace = 'alephbet';

        experiment = new AlephBet.Experiment({
            name: 'my a/b test',
            tracking_adapter: new AlephBet.Gimel(track_url, namespace),
            // trigger: function() { ... },  // optional trigger
            variants: {
                'red': function() {
                    // add your code here
                },
                'blue': function() {
                    // add your code here
                }
            }
        });
        </script>
        """ % locals()
    )


def dashboard_url(namespace='alephbet'):
    api_id = get_create_api()
    api_region = region()
    endpoint = EXPERIMENTS_ENDPOINT
    experiments_url = 'https://{}.execute-api.{}.amazonaws.com/prod/{}'.format(
        api_id, api_region, endpoint)
    return ('https://codepen.io/anon/pen/LOGGZj/?experiment_url={}'
            '&api_key={}&namespace={}').format(experiments_url,
                                               get_api_key(),
                                               namespace)


def preflight_checks():
    logger.info('checking aws credentials and region')
    if region() is None:
        logger.error('Region is not set up. please run aws configure')
        return False
    try:
        check_aws_credentials()
    except AttributeError:
        logger.error('AWS credentials not found. please run aws configure')
        return False
    logger.info('testing redis')
    try:
        _redis().ping()
    except redis.exceptions.ConnectionError:
        logger.error('Redis ping failed. Please run gimel configure')
        return False
    return True


def run():
    prepare_zip()
    api_id = get_create_api()
    role_arn = role()
    for component in WIRING:
        function_arn = create_update_lambda(role_arn, component['lambda'])
        create_update_api(role_arn, function_arn, component['api_gateway'])
    deploy_api(api_id)
    api_key(api_id)


if __name__ == '__main__':
    try:
        preflight_checks()
        run()
        js_code_snippet()
    except Exception:
        logger.error('preflight checks failed')
