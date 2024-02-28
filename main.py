import json
import boto3


SESSION_KEY={
    "aws_access_key_id":"",
        "aws_secret_access_key":"",
        "aws_session_token":""
    
}

class GetEc2Info:
    def __init__(self,accountId):
        self.sts_client=boto3.client('sts');

        #get session to target aws account.
        response = self.sts_client.assume_role(
            RoleArn=get_ssm_parameters_role(accountId),
            RoleSessionName="temp-session"
            )
        #set aws access config
        SESSION_KEY["aws_access_key_id"]=response['Credentials']['AccessKeyId']
        SESSION_KEY["aws_secret_access_key"]=response['Credentials']['SecretAccessKey']
        SESSION_KEY["aws_session_token"]=response['Credentials']['SessionToken']
        
    def get_ec2_name(self,instanceId):
        #get target instance tags (Alarm tags)
        ec2_name=instanceId
        ec2_client=boto3.client('ec2',  aws_access_key_id=SESSION_KEY["aws_access_key_id"],
        aws_secret_access_key=SESSION_KEY["aws_secret_access_key"],
        aws_session_token=SESSION_KEY["aws_session_token"]
        )

        #ec2_client=boto3.client('ec2');
        ec2_info=ec2_client.describe_instances(InstanceIds=[instanceId])
        for tags in ec2_info['Reservations'][0]['Instances'][0]['Tags']:
            if tags['Key'] == 'Name':
                ec2_name=tags['Value']

        return ec2_name


    def get_ec2_type(self,instanceId):
        #get target instance tags (Alarm tags)
        ec2_name=instanceId
        ec2_client=boto3.client('ec2',  aws_access_key_id=SESSION_KEY["aws_access_key_id"],
        aws_secret_access_key=SESSION_KEY["aws_secret_access_key"],
        aws_session_token=SESSION_KEY["aws_session_token"]
        )

        #ec2_client=boto3.client('ec2');
        ec2_info=ec2_client.describe_instances(InstanceIds=[instanceId])
        return ec2_info['Reservations'][0]['Instances'][0]['InstanceType']
        

def get_ssm_parameters_role(accountId):
    ssm_client = boto3.client('ssm');
    chnl_name=ssm_client.get_parameters(Names=['CW_IAM_ROLE_ARN'])['Parameters'];
    value=chnl_name[0]['Value']
    # using json.loads()
    # convert dictionary string to dictionary
    res = json.loads(value)
    print("IAM_ROLE_ARN : "+res[accountId])
    return res[accountId]


def get_ssm_parameters(accountId):
    ssm_client = boto3.client('ssm');
    svc_name=ssm_client.get_parameters(Names=['SERVICE_NAME'])['Parameters'];
    value=svc_name[0]['Value']
    res = json.loads(value)
    
    return res[accountId]

def runEventMsg(detail):
    ec2_client=GetEc2Info(detail['userIdentity']['accountId']);
    user=detail['userIdentity']['arn'].split('/')[-1]
    eventName=detail['eventName']
    region=detail['awsRegion']
    client = boto3.client('sns')
    
    for i in detail['responseElements']['instancesSet']['items']:
        ec2_tags=[tag for tag in i['tagSet']['items'] if tag['key'] == 'Name']
        ec2_name=ec2_tags[0]['value'] if len(ec2_tags) > 0 else "UNKNOWN";
        
        msg = {
    "version": "1.0",
    "source": "custom",
    "content": {
         "description": ":warning: *"+get_ssm_parameters(detail['userIdentity']['accountId'])+
        "*\n*Event Time*\n"+
        detail['eventTime'] +
        "\n*EC2 Name*\n"+
        ec2_name+
        "\n*EC2 ID*\n"+
        i['instanceId']+
        "\n*EC2 Type*\n"+
        i['instanceType']+
        "\n*User name*\n"+
        user+        
        "\n*Event Mesage*\n"+
        eventName

    }
    }
        response = client.publish(
        TargetArn="arn:aws:sns:ap-northeast-2:589566835476:SNS_TOPIC_EC2_STATE_EVENT",
        Message=json.dumps({'default': json.dumps(msg)}),
        MessageStructure='json'
        )
    return msg;
    
    

def otherEventMsg(detail):
    ec2_client=GetEc2Info(detail['userIdentity']['accountId']);
    user=detail['userIdentity']['arn'].split('/')[-1]
    eventName=detail['eventName']
    region=detail['awsRegion']
    client = boto3.client('sns')
    
    for i in detail['requestParameters']['instancesSet']['items']:
        
        msg = {
    "version": "1.0",
    "source": "custom",
    "content": {
         "description": ":warning: *"+get_ssm_parameters(detail['userIdentity']['accountId'])+
        "*\n*Event Time*\n"+
        detail['eventTime'] +
        "\n*EC2 Name*\n"+
        ec2_client.get_ec2_name(i['instanceId'])+
        "\n*EC2 ID*\n"+
        i['instanceId']+        
        "\n*EC2 Type*\n"+
        ec2_client.get_ec2_type(i['instanceId'])+
        "\n*User name*\n"+
        user+        
        "\n*Event Mesage*\n"+
        eventName
    }
    }
        response = client.publish(
        TargetArn="arn:aws:sns:ap-northeast-2:589566835476:SNS_TOPIC_EC2_STATE_EVENT",
        Message=json.dumps({'default': json.dumps(msg)}),
        MessageStructure='json'
        )
    return msg;
    
def spotEventMsg(spot_event,instance_id,time,account):
    client = boto3.client('sns')
    ec2_client=GetEc2Info(account);
    eventName=spot_event
    msg = {
    "version": "1.0",
    "source": "custom",
    "content": {
         "description": ":warning: *"+get_ssm_parameters(account)+" Spot Instance 이벤트 발생"+
        "*\n*Event Time*\n"+
        time +
        "\n*EC2 Name*\n"+
        ec2_client.get_ec2_name(instance_id)+
        "\n*EC2 ID*\n"+
        instance_id+        
        "\n*EC2 Type*\n"+
        ec2_client.get_ec2_type(instance_id)+
#        "\n*User name*\n"+
#        user+        
        "\n*Event Mesage*\n"+
        eventName
    }
    }
        
    response = client.publish(
        TargetArn="arn:aws:sns:ap-northeast-2:589566835476:SNS_TOPIC_EC2_SPOT_EVENT",
        Message=json.dumps({'default': json.dumps(msg)}),
        MessageStructure='json'
        )

def lambda_handler(event, context):
    detail=event['detail']
    if event['detail-type'] == "EC2 Spot Instance Interruption Warning" or event['detail-type'] == "EC2 Instance Rebalance Recommendation":
        spotEventMsg(event['detail-type'],detail['instance-id'],event['time'],event['account'])

        return print("SPOT EVENT !")

    elif detail['userIdentity']['accountId'] == '744690697308' and detail['userIdentity']['arn'].split('/')[-1] == 'AutoScaling':
        return print("NDC's AutoScaling");
    elif detail['userIdentity']['accountId'] == '111111111111' and detail['userIdentity']['arn'].split('/')[-1] == 'AutoScaling':
        return print("HOT's AutoScaling");
    else:
        msg=runEventMsg(detail) if detail['eventName'] == "RunInstances" else otherEventMsg(detail);

    #msg=runEventMsg(detail) if detail['eventName'] == "RunInstances" else otherEventMsg(detail);
    #print(json.dumps(msg));

    return {
        'statusCode': 200,
        'body': json.dumps(msg)
    }

