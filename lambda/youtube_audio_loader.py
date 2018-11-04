from __future__ import print_function

import json
import boto3
import botocore

batch_client = boto3.client('batch')

def lambda_handler(event, context):
    # Log the received event
    print("Received event: " + json.dumps(event, indent=2))
        
    command = ["--query_string", event['query_string'],
               "--bucket_name", event['bucket_name'],
               "--working_dir", event['working_dir']
               ]

    job_definition = event['jobDefinition']
    job_name = event['job_name']
    job_queue = event['jobQueue']
    container_overrides = {'command': command,}
    depends_on = event['dependsOn'] if event.get('dependsOn') else []

    try:
        response = batch_client.submit_job(
            jobDefinition=job_definition,
            jobName=job_name,
            jobQueue=job_queue,
            dependsOn=depends_on,
            containerOverrides=container_overrides
        )
        
        # Log response from AWS Batch
        print("Response: " + json.dumps(response, indent=2))
        
        # Return the jobId
        event['jobId'] = response['jobId']
        return event
    
    except Exception as e:
        print(e)
        message = 'Error submitting job - youtube_audio_loader'
        print(message)
        raise Exception(message)
