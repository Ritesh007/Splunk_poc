#########################################################################################
# Runs every minute and collects the events from SQS and drops in S3
# Lambda config - 
#          Cloudwatch bridge with rate(1 minute) to run every minute
#          Memory 512MB
#          Timeout 10seconds
#          Async queue timeout 1 minute (as this runs every minute)
#          Retries 0 (as this runs every minute)
#          Dead letter queue - not to be configured
#          Python 3.7
#Lambda concurrency -
#         Reserved concurrency 1 as this runs once every minute
#Lambda Logs -
#         Cloudwatch Group
#         SNS notification on errors
#Lambda environment variables -
#          key - SPLUNK_BACKUP_BUCKET       value - <name_of_s3_bucket>
#          key - SPLUNK_BACKUP_BUCKET_KEY   value - <name_start_of_the_s3_bucket_key> 
#Lambda IAM role permissions - 
#        SQS read message and delete message acces 
#        Cloudwatch log write access
#        S3 put object access
#Lambda Networking -
#       Must be connected to a VPC
############################################################################################
import json
import boto3
import os
from datetime import datetime

def lambda_handler(event, context):
    sqs_client = boto3.client('sqs')
    s3_client = boto3.client('s3')
    datetime_now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    messages = []
    body = []
    s3_backup_bucket = os.environ['SPLUNK_BACKUP_BUCKET']
    s3_backup_key = os.environ['SPLUNK_BACKUP_BUCKET_KEY']
    # read message from sqs queue
    while True:
        resp = sqs_client.receive_message(
            QueueUrl='https://sqs.us-west-2.amazonaws.com/339257130022/splunk',
            AttributeNames=[ "All" ],
            MaxNumberOfMessages=1
            )

        try:
            messages.extend(resp['Messages'])
        except KeyError:
            # if body not null send the messages to s3
            if len(body) != 0:
                s3_client.put_object(
                    Body= bytes(json.dumps(body).encode('UTF-8')),
                    Bucket= s3_backup_bucket,
                    Key= s3_backup_key+"."+datetime_now)
            break
        
        for msg in resp['Messages']:
            entries = [ {'Id': msg['MessageId'], 'ReceiptHandle': msg['ReceiptHandle']}]
            body.append(msg['Body'])
            
        # delete the read message from sqs queue
        resp = sqs_client.delete_message_batch(
                QueueUrl="https://sqs.us-west-2.amazonaws.com/339257130022/splunk", Entries=entries
                )
                    
        if len(resp['Successful']) != len(entries):
            raise RuntimeError( f"Failed to delete messages: entries={entries!r} resp={resp!r}")
    
    return resp["ResponseMetadata"]["HTTPStatusCode"]