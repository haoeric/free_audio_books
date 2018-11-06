#!/usr/bin/env bash

########################################################################
## AWS batch enviroment setup for Alexa skill - Daily Digest
## Chen Hao, 6/10/2018 
########################################################################

##----------------------------------------------------------------------------
## Parameters 
##----------------------------------------------------------------------------

# ECR registry (region specific)
REGISTRY=012532289196.dkr.ecr.ap-southeast-2.amazonaws.com
KEYNAME=haoeric-alexa-ec2                                      
VPCID=vpc-dd2a3fb9                                            
SUBNETS=subnet-11e52c58,subnet-2e33ed49,subnet-74eedf2d       
SECGROUPS=sg-430a6125                                         

# IAM roles for batch (global shared)
SERVICEROLE=arn:aws:iam::012532289196:role/iam-awsBatchServiceRole-1PY62Y60413WM
INSTANCEROLE=arn:aws:iam::012532289196:instance-profile/iam-ecsInstanceRole-18P3U9TL1H262
IAMFLEETROLE=arn:aws:iam::012532289196:role/iam-spotFleetRole-7ST64BEKXAZ
JOBROLEARN=arn:aws:iam::012532289196:role/iam-ecsTaskRole-1BIYRLSWKSLGO

## create a custom AMI with attached 1TB EBS
## EBS mount configure
# sudo yum -y update
# # Check the device name
# sudo fdisk -l
# # Make directory to where you want to mount the volume
# sudo mkdir /docker_scratch
# # Create filesystem on your volume 
# sudo mkfs.ext4 /dev/xvdb
# # Mount volume
# sudo mount -t ext4 /dev/xvdb /docker_scratch
# # If you want to preserve the mount after e.g. a restart, open /etc/fstab and add the mount to it
# ## note the following path /dev/xvdb may change case by case
# echo "/dev/xvdb /docker_scratch auto noatime 0 0" | sudo tee -a /etc/fstab
# # Make sure nothing is wrong with fstab by mounting all
# mount -a


#-----------------------------------------------------------------------------------------------
Create a Batch compute environment (spot) - 1TB common vCPU config (optimal)  
------------------------------------------------------------------------------------------------

# Create a batch compute environment
ENVNAME=haoeric-sydney-1TB-optimal-spot     # environment name  
EC2TYPE=SPOT                                # instance resource type
MAXCPU=100                                  # max vCPUs in compute environment
SPOTPER=70                                  # percentage of on demand
IMAGEID=ami-0c9f509ab0b5ed5ec               # custom image with extra mounted EBS volumn
instanceTypes=optimal   

aws batch create-compute-environment \
--compute-environment-name ${ENVNAME} \
--type MANAGED --state ENABLED \
--service-role ${SERVICEROLE} \
--compute-resources type=${EC2TYPE},minvCpus=0,maxvCpus=${MAXCPU},desiredvCpus=0,instanceTypes=${instanceTypes},imageId=${IMAGEID},subnets=${SUBNETS},securityGroupIds=${SECGROUPS},ec2KeyPair=${KEYNAME},instanceRole=${INSTANCEROLE},bidPercentage=${SPOTPER},spotIamFleetRole=${IAMFLEETROLE}

# Create the job queues
aws batch create-job-queue --job-queue-name highPriority-${ENVNAME} \
--compute-environment-order order=0,computeEnvironment=${ENVNAME} --priority 1 --state ENABLED



##----------------------------------------------------------------------------
## Rejister job definition
##----------------------------------------------------------------------------

## register the job
JOBNAME="youtube_audio_loader"
CONTAINERNAME="audio_books_crawler"
JOBMEMORY=2000
JOBCPUS=2

aws batch register-job-definition \
--job-definition-name ${JOBNAME} \
--type container --retry-strategy attempts=3 \
--container-properties '
{"image": "'${REGISTRY}'/'${CONTAINERNAME}'",
"jobRoleArn": "'${JOBROLEARN}'",
"memory": '${JOBMEMORY}',
"vcpus": '${JOBCPUS}',
"mountPoints": [{"containerPath": "/scratch", "readOnly": false, "sourceVolume": "docker_scratch"}],
"volumes": [{"name": "docker_scratch", "host": {"sourcePath": "/docker_scratch"}}]
}'

