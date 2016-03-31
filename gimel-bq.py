import boto3
import json
import base64
import sys
sys.path.insert(0, './vendor')
from bigquery import BIGQUERY_SCOPE, get_client
from oauth2client.service_account import ServiceAccountCredentials
from config import config


def _bq():
    bq_json = config['big_query']['json']
    # a hack to get around get_client not working...
    # see https://github.com/google/oauth2client/issues/401
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        bq_json,
        scopes=[BIGQUERY_SCOPE])
    return get_client(bq_json['project_id'], credentials=credentials)

bigquery_client = _bq()
kinesis = boto3.client('kinesis')


def _track_kinesis(event):
    kinesis.put_record(
        StreamName=config['kinesis']['stream'],
        Data=json.dumps(event),
        PartitionKey="{0}:{1}".format(event['namespace'], event['experiment'])
    )


def track(event, context):
    """ tracks an alephbet event (participate, goal etc)
        and pushes it to the kinesis stream
        params:
            - experiment - name of the experiment
            - uuid - a unique id for the event
            - variant - the name of the variant
            - event - either the goal name or 'participate'
            - namespace (optional)
    """
    tracking = {}
    tracking['namespace'] = event.get('namespace', 'alephbet')
    for k in ['experiment', 'variant', 'event', 'uuid']:
        tracking[k] = event[k]
    _track_kinesis(tracking)


def kinesis_ingest(event, context):
    """ ingests the kinesis event stream and pushes to BigQuery
    """
    events = [json.loads(base64.b64decode(x['kinesis']['data']))
              for x in event['Records']]
    bigquery_client.push_rows(config['big_query']['dataset'],
                              config['big_query']['table'],
                              events,
                              'uuid')
    print('Successfully processed {} records.'.format(len(event['Records'])))
