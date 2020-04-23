#########################################################################################
# Ports logs from S3 to splunk by calling the cloudwatchlogs_to_splunk Lambda
# and deletes the S3 objects once ported. 
# This Lambda should be manually triggered.
#
# Lambda config - 
#          Memory 512MB
#          Timeout 10seconds
#          Async queue timeout 1 minute (as this is a manual run)
#          Retries 0 (as this is a maunal run)
#          Dead letter queue - not to be configured
#          Python 3.7
#Lambda concurrency -
#         Use unreserved account concurrency
#Lambda Logs -
#         Cloudwatch Group
#         SNS notification on errors
#Lambda environment variables -
#          key - SPLUNK_BACKUP_BUCKET       value - <name_of_s3_bucket>
#Lambda IAM role permissions - 
#        Cloudwatch log write access
#        S3 get and delete object access
#        Invoke access to cloudwatchlogs_to_splunk lambda
#Lambda Networking -
#       Must be connected to a VPC
############################################################################################

import json
import boto3
import os

s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')
s3_backup_bucket = os.environ['SPLUNK_BACKUP_BUCKET']

def lambda_handler(event, context):
    for key in get_s3_keys(s3_backup_bucket):
        #get object data from s3
        resp_obj=s3_client.get_object(Bucket=s3_backup_bucket, Key=key)
        #stream it to splunk lambda
        event_list = resp_obj['Body'].read().decode('utf-8').strip('][').split(',')
        for events in event_list:
            response_lambda = lambda_client.invoke( FunctionName='splunk_sqs', InvocationType='Event',Payload=json.loads(events))
        #delete the streamed objects in s3 if the lambda invoke returned 2xx
        if 200 <= response_lambda["ResponseMetadata"]["HTTPStatusCode"] <= 299:
            response = s3_client.delete_object(Bucket=s3_backup_bucket, Key=key)
        
    return response["ResponseMetadata"]["HTTPStatusCode"]

# list s3 keys
def get_s3_keys(bucket):
    kwargs = {'Bucket': bucket}
    while True:
        resp = s3_client.list_objects_v2(**kwargs)
        for obj in resp['Contents']:
            yield obj['Key']
        try:
            kwargs['ContinuationToken'] = resp['NextContinuationToken']
        except KeyError:
            break