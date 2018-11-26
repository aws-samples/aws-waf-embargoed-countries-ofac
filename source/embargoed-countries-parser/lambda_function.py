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
from os import environ

def update_conditions(geo_match_set_id, ip_set_id, bucket_name, object_key):
    logging.getLogger().debug("update_conditions - Start")

    s3_client = boto3.client('s3')
    waf_client = boto3.client(environ['API_TYPE'])

    #--------------------------------------------------------------------------
    # Get updated embargoed countries and IPs from S3 file
    #--------------------------------------------------------------------------
    file_name =  object_key.split('/')[-1]
    local_file_path = '/tmp/%s'%file_name
    s3_client.download_file(bucket_name, object_key, local_file_path)

    # create country list
    json_data = json.loads(open(local_file_path).read())

    json_embargoed_countries = [e['code'] for e in json_data['embargoed-countries']]
    json_embargoed_ips = {}
    for e in json_data['embargoed-ips']:
        for ip in e['ips']:
            json_embargoed_ips[ip['Value']] = ip['Type']

    #--------------------------------------------------------------------------
    # Get curently blocked countries and IPs on AWS WAF
    #--------------------------------------------------------------------------
    response = waf_client.get_geo_match_set(GeoMatchSetId = geo_match_set_id)
    waf_embargoed_countries = [e['Value'] for e in response['GeoMatchSet']['GeoMatchConstraints'] if e['Type'] == 'Country']

    waf_embargoed_ips = {}
    response = waf_client.get_ip_set(IPSetId = ip_set_id)
    for e in response['IPSet']['IPSetDescriptors']:
        waf_embargoed_ips[e['Value']] = e['Type']

    #--------------------------------------------------------------------------
    # Update AWS WAF list to aligned with what is set on S3 file
    #--------------------------------------------------------------------------
    updates = {"countries":[], "ips":[]}
    embargoed_countries_removed = list(set(waf_embargoed_countries) - set(json_embargoed_countries))
    for c in embargoed_countries_removed:
        updates["countries"].append({'Action': 'DELETE', 'GeoMatchConstraint': {'Type': 'Country', 'Value': c}})

    embargoed_countries_added = list(set(json_embargoed_countries) - set(waf_embargoed_countries))
    for c in embargoed_countries_added:
        updates["countries"].append({'Action': 'INSERT', 'GeoMatchConstraint': {'Type': 'Country', 'Value': c}})

    if len(updates["countries"]) > 0:
        response = waf_client.update_geo_match_set(
            GeoMatchSetId = geo_match_set_id,
            ChangeToken = waf_client.get_change_token()['ChangeToken'],
            Updates = updates["countries"]
        )

    embargoed_ips_removed = list(set(waf_embargoed_ips) - set(json_embargoed_ips))
    for c in embargoed_ips_removed:
        updates["ips"].append({'Action': 'DELETE', 'IPSetDescriptor': {'Type': waf_embargoed_ips[c], 'Value': c}})

    embargoed_ips_added = list(set(json_embargoed_ips) - set(waf_embargoed_ips))
    for c in embargoed_ips_added:
        updates["ips"].append({'Action': 'INSERT', 'IPSetDescriptor': {'Type': json_embargoed_ips[c], 'Value': c}})

    if len(updates["ips"]) > 0:
        response = waf_client.update_ip_set(
            IPSetId = ip_set_id,
            ChangeToken = waf_client.get_change_token()['ChangeToken'],
            Updates = updates["ips"]
       )

    logging.getLogger().debug("update_conditions - End")

def lambda_handler(event, context):
    result = {
        'statusCode': '200',
        'body':  {'message': 'success'}
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
        geo_match_set_id = environ['GEO_MATCH_SET_ID']
        ip_set_id = environ['IP_SET_ID']
        bucket_name = event['Records'][0]['s3']['bucket']['name']
        object_key =  event['Records'][0]['s3']['object']['key']

        #----------------------------------------------------------
        # Process file
        #----------------------------------------------------------
        update_conditions(geo_match_set_id, ip_set_id, bucket_name, object_key)

        return json.dumps(result)

    except Exception as error:
        result = {
            'statusCode': '500',
            'body':  {'message': error.message}
        }

    return json.dumps(result)
