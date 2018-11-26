#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#  Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.   #
#                                                                            #
#  Licensed under the Amazon Software License (the "License"). You may not   #
#  use this file except in compliance with the License. A copy of the        #
#  License is located at                                                     #
#                                                                            #
#      http://aws.amazon.com/asl/                                            #
#                                                                            #
#  or in the "license" file accompanying this file. This file is distributed #
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,        #
#  express or implied. See the License for the specific language governing   #
#  permissions and limitations under the License.                            #
##############################################################################

import boto3
import logging
import json
from botocore.vendored import requests
from os import environ

def send_response(event, context, responseStatus, responseData, resourceId, reason=None):
    logging.getLogger().debug("send_response - Start")

    responseUrl = event['ResponseURL']
    logging.getLogger().debug(responseUrl)

    cw_logs_url = "https://console.aws.amazon.com/cloudwatch/home?region=%s#logEventViewer:group=%s;stream=%s"%(context.invoked_function_arn.split(':')[3], context.log_group_name, context.log_stream_name)
    logging.getLogger().debug("Logs: cw_logs_url")

    responseBody = {}
    responseBody['Status'] = responseStatus
    responseBody['Reason'] = reason or ('See the details in CloudWatch Logs: ' +  cw_logs_url)
    responseBody['PhysicalResourceId'] = resourceId
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    responseBody['NoEcho'] = False
    responseBody['Data'] = responseData

    json_responseBody = json.dumps(responseBody)

    logging.getLogger().debug("Response body:\n" + json_responseBody)

    headers = {
        'content-type' : '',
        'content-length' : str(len(json_responseBody))
    }

    try:
        response = requests.put(responseUrl,
                                data=json_responseBody,
                                headers=headers)
        logging.getLogger().debug("Status code: " + response.reason)

    except Exception as error:
        logging.getLogger().error("send(..) failed executing requests.put(..): " + str(error))

    logging.getLogger().debug("send_response - End")

def clean_ip_set(ip_set_id):
    logging.getLogger().debug("clean_ip_set - Start")

    waf_client = boto3.client(environ['API_TYPE'])
    updates = []
    response = waf_client.get_ip_set(IPSetId = ip_set_id)
    for e in response['IPSet']['IPSetDescriptors']:
        updates.append({
            'Action': 'DELETE',
            'IPSetDescriptor': {
                'Type': e['Type'],
                'Value': e['Value']
            }
        })

    if len(updates) > 0:
        response = waf_client.update_ip_set(
            IPSetId = ip_set_id,
            ChangeToken = waf_client.get_change_token()['ChangeToken'],
            Updates = updates
        )

    logging.getLogger().debug("clean_ip_set - End")

def create_geo_match_set(parent_stack_name):
    logging.getLogger().debug("create_geo_match_set - Start")

    waf_client = boto3.client(environ['API_TYPE'])
    response = waf_client.create_geo_match_set(
        Name=parent_stack_name,
        ChangeToken=waf_client.get_change_token()['ChangeToken']
    )

    logging.getLogger().debug("create_geo_match_set - End")
    return response['GeoMatchSet']['GeoMatchSetId']

def clean_geo_match_set(geo_match_set_id):
    logging.getLogger().debug("clean_geo_match_set - Start")

    waf_client = boto3.client(environ['API_TYPE'])
    updates = []
    response = waf_client.get_geo_match_set(GeoMatchSetId=geo_match_set_id)
    for c in response['GeoMatchSet']['GeoMatchConstraints']:
        updates.append({
            'Action': 'DELETE',
            'GeoMatchConstraint': {
                'Type': c['Type'],
                'Value': c['Value']
            }
        })

    if len(updates) > 0:
        response = waf_client.update_geo_match_set(
            GeoMatchSetId = geo_match_set_id,
            ChangeToken = waf_client.get_change_token()['ChangeToken'],
            Updates = updates
        )

    logging.getLogger().debug("clean_geo_match_set - End")

def delete_geo_match_set(geo_match_set_id):
    logging.getLogger().debug("delete_geo_match_set - Start")

    clean_geo_match_set(geo_match_set_id)

    waf_client = boto3.client(environ['API_TYPE'])
    response = waf_client.delete_geo_match_set(
        GeoMatchSetId=geo_match_set_id,
        ChangeToken=waf_client.get_change_token()['ChangeToken']
    )

    logging.getLogger().debug("delete_geo_match_set - End")

def configure_embargoed_countries_bucket(oring_bucket, embargoed_countries_bucket, embargoed_countries_key, countries_parser_arn):
    logging.getLogger().debug("configure_embargoed_countries_bucket - Start")
    logging.getLogger().debug("oring_bucket: %s"%oring_bucket)
    logging.getLogger().debug("embargoed_countries_bucket: %s"%embargoed_countries_bucket)
    logging.getLogger().debug("embargoed_countries_key: %s"%embargoed_countries_key)
    logging.getLogger().debug("countries_parser_arn: %s"%countries_parser_arn)

    # Configure bucket event to call embargoed countries parser
    file_name =  embargoed_countries_key.split('/')[-1]
    file_name_parts = file_name.rsplit('.', 1)
    notification_conf = {'LambdaFunctionConfigurations':[{
        'Id': 'Call embargoed countries parser',
        'LambdaFunctionArn': countries_parser_arn,
        'Events': ['s3:ObjectCreated:*'],
        'Filter': {'Key': {'FilterRules': [
            {'Name': 'prefix','Value': file_name_parts[0]},
            {'Name': 'suffix','Value': file_name_parts[1]}
        ]}}
    }]}
    s3_client = boto3.client('s3')
    response = s3_client.put_bucket_notification_configuration(Bucket=embargoed_countries_bucket, NotificationConfiguration=notification_conf)

    # upload embargoed-countries.json
    file_name =  embargoed_countries_key.split('/')[-1]
    local_file_path = '/tmp/%s'%file_name

    prefix = 'https://s3.amazonaws.com/' + oring_bucket + '/'
    response = requests.head(prefix + embargoed_countries_key)
    region_code = response.headers['x-amz-bucket-region']
    if region_code != 'us-east-1':
        prefix = prefix.replace('https://s3', 'https://s3-'+region_code)
    response = requests.get(prefix + embargoed_countries_key)
    open(local_file_path, 'wb').write(response.content)

    s3_client = boto3.client('s3')
    s3_client.upload_file(local_file_path, embargoed_countries_bucket, file_name)

    logging.getLogger().debug("configure_embargoed_countries_bucket - End")

def rollback_embargoed_countries_bucket_configuration(embargoed_countries_bucket, embargoed_countries_key):
    logging.getLogger().debug("rollback_embargoed_countries_bucket_configuration - Start")

    # Clean bucket event configuration
    s3_client = boto3.client('s3')
    notification_conf = {}
    response = s3_client.put_bucket_notification_configuration(Bucket=embargoed_countries_bucket, NotificationConfiguration=notification_conf)

    # delete embargoed-countries.json
    file_name = embargoed_countries_key.split('/')[-1]
    s3_client = boto3.client('s3')
    s3_client.delete_object(Bucket=embargoed_countries_bucket, Key=file_name)

    logging.getLogger().debug("rollback_embargoed_countries_bucket_configuration - End")

def associate_waf_resources(web_acl_id, rule_action, ip_set_id, rule_id_ip, rule_priority_ip, geo_match_set_id, rule_id_geo, rule_priority_geo):
    logging.getLogger().debug("associate_waf_resources - Start")

    waf_client = boto3.client(environ['API_TYPE'])
    waf_client.update_rule(
        RuleId = rule_id_geo,
        ChangeToken = waf_client.get_change_token()['ChangeToken'],
        Updates = [{
            'Action': 'INSERT',
            'Predicate': {
                'Negated': False,
                'Type': 'GeoMatch',
                'DataId': geo_match_set_id
            }
        }]
    )

    response = waf_client.get_web_acl(WebACLId = web_acl_id)
    waf_client.update_web_acl(
        WebACLId = web_acl_id,
        ChangeToken = waf_client.get_change_token()['ChangeToken'],
        Updates = [{
            'Action': 'INSERT',
            'ActivatedRule': {
                'Priority': rule_priority_geo,
                'RuleId': rule_id_geo,
                'Action': {'Type': rule_action},
                'Type': 'REGULAR'
            }
        }],
        DefaultAction = response['WebACL']['DefaultAction']
    )

    logging.getLogger().debug("associate_waf_resources - End")

def disassociate_waf_resources(web_acl_id, rule_action, ip_set_id, rule_id_ip, rule_priority_ip, geo_match_set_id, rule_id_geo, rule_priority_geo):
    logging.getLogger().debug("disassociate_waf_resources - Start")
    waf_client = boto3.client(environ['API_TYPE'])

    try:
        waf_client.update_rule(
            RuleId = rule_id_geo,
            ChangeToken = waf_client.get_change_token()['ChangeToken'],
            Updates = [{
                'Action': 'DELETE',
                'Predicate': {
                    'Negated': False,
                    'Type': 'GeoMatch',
                    'DataId': geo_match_set_id
                }
            }]
        )
    except Exception as error:
        logging.getLogger().error(str(error))

    try:
        response = waf_client.get_web_acl(WebACLId = web_acl_id)
        waf_client.update_web_acl(
            WebACLId = web_acl_id,
            ChangeToken = waf_client.get_change_token()['ChangeToken'],
            Updates = [{
                'Action': 'DELETE',
                'ActivatedRule': {
                    'Priority': rule_priority_geo,
                    'RuleId': rule_id_geo,
                    'Action': {'Type': rule_action},
                    'Type': 'REGULAR'
                }
            }],
            DefaultAction = response['WebACL']['DefaultAction']
        )
    except Exception as error:
        logging.getLogger().error(str(error))

    logging.getLogger().debug("disassociate_waf_resources - End")

def lambda_handler(event, context):
    responseStatus = 'SUCCESS'
    reason = None
    responseData = {}
    result = {
        'StatusCode': '200',
        'Body':  {'message': 'success'}
    }

    try:
        #------------------------------------------------------------------
        # Set Log Level
        #------------------------------------------------------------------
        global log_level
        log_level = str(environ['LOG_LEVEL'].upper())
        if log_level not in ['DEBUG', 'INFO','WARNING', 'ERROR','CRITICAL']:
            log_level = 'ERROR'
        logging.getLogger().setLevel(log_level)

        #----------------------------------------------------------
        # Read inputs parameters
        #----------------------------------------------------------
        logging.getLogger().info(event)
        request_type = event['RequestType'].upper()  if ('RequestType' in event) else ""
        logging.getLogger().info(request_type)

        if event['ResourceType'] == "Custom::GeoMatchSet":
            parent_stack_name = event['ResourceProperties']['ParentStackName']

            if 'CREATE' in request_type:
                geo_match_set_id = create_geo_match_set(parent_stack_name)
                responseData['Id'] = geo_match_set_id

        elif event['ResourceType'] == "Custom::CountriesParserEvent":
            countries_parser_arn = event['ResourceProperties']['CountriesParserArn']
            oring_bucket = event['ResourceProperties']['OringBucket']
            embargoed_countries_bucket = event['ResourceProperties']['EmbargoedCountriesBucket']
            embargoed_countries_key = event['ResourceProperties']['EmbargoedCountriesKey']

            if 'CREATE' in request_type:
                configure_embargoed_countries_bucket(oring_bucket, embargoed_countries_bucket, embargoed_countries_key, countries_parser_arn)

            elif 'UPDATE' in request_type:
                rollback_embargoed_countries_bucket_configuration(embargoed_countries_bucket, embargoed_countries_key)
                configure_embargoed_countries_bucket(oring_bucket, embargoed_countries_bucket, embargoed_countries_key, countries_parser_arn)

            elif 'DELETE' in request_type:
                rollback_embargoed_countries_bucket_configuration(embargoed_countries_bucket, embargoed_countries_key)

        elif event['ResourceType'] == "Custom::WafAssociations":
            web_acl_id = event['ResourceProperties']['WebAclId'].strip()
            rule_action = event['ResourceProperties']['RuleAction']
            ip_set_id = event['ResourceProperties']['IpSetId']
            rule_id_ip = event['ResourceProperties']['RuleIdIp']
            rule_priority_ip = int(event['ResourceProperties']['RulePriorityIp'])
            geo_match_set_id = event['ResourceProperties']['GeoMatchSetId']
            rule_id_geo = event['ResourceProperties']['RuleIdGeo']
            rule_priority_geo = int(event['ResourceProperties']['RulePriorityGeo'])

            if 'CREATE' in request_type:
                associate_waf_resources(web_acl_id, rule_action, ip_set_id, rule_id_ip, rule_priority_ip, geo_match_set_id, rule_id_geo, rule_priority_geo)

            elif 'UPDATE' in request_type:
                web_acl_id = event['OldResourceProperties']['WebAclId'].strip()
                rule_action = event['OldResourceProperties']['RuleAction']
                ip_set_id = event['OldResourceProperties']['IpSetId']
                rule_id_ip = event['OldResourceProperties']['RuleIdIp']
                rule_priority_ip = int(event['OldResourceProperties']['RulePriorityIp'])
                geo_match_set_id = event['OldResourceProperties']['GeoMatchSetId']
                rule_id_geo = event['OldResourceProperties']['RuleIdGeo']
                rule_priority_geo = int(event['OldResourceProperties']['RulePriorityGeo'])
                disassociate_waf_resources(web_acl_id, rule_action, ip_set_id, rule_id_ip, rule_priority_ip, geo_match_set_id, rule_id_geo, rule_priority_geo)

                web_acl_id = event['ResourceProperties']['WebAclId'].strip()
                rule_action = event['ResourceProperties']['RuleAction']
                ip_set_id = event['ResourceProperties']['IpSetId']
                rule_id_ip = event['ResourceProperties']['RuleIdIp']
                rule_priority_ip = int(event['ResourceProperties']['RulePriorityIp'])
                geo_match_set_id = event['ResourceProperties']['GeoMatchSetId']
                rule_id_geo = event['ResourceProperties']['RuleIdGeo']
                rule_priority_geo = int(event['ResourceProperties']['RulePriorityGeo'])
                associate_waf_resources(web_acl_id, rule_action, ip_set_id, rule_id_ip, rule_priority_ip, geo_match_set_id, rule_id_geo, rule_priority_geo)

            elif 'DELETE' in request_type:
                disassociate_waf_resources(web_acl_id, rule_action, ip_set_id, rule_id_ip, rule_priority_ip, geo_match_set_id, rule_id_geo, rule_priority_geo)
                clean_ip_set(ip_set_id)
                delete_geo_match_set(geo_match_set_id)

    except Exception as error:
        logging.getLogger().error(str(error))
        responseStatus = 'FAILED'
        reason = error.message
        result = {
            'statusCode': '500',
            'body':  {'message': error.message}
        }

    finally:
        #------------------------------------------------------------------
        # Send Result
        #------------------------------------------------------------------
        if 'ResponseURL' in event:
            send_response(event, context, responseStatus, responseData, event['LogicalResourceId'], reason)

        return json.dumps(result)
