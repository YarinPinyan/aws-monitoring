import boto3
from boto3 import Session
from typing import Dict, List
import json

# region constants
INTERNET_FACING: str = "internet-facing"
DEFAULT_AWS_REGION: str = "us-east-1"
# endregion

LoadBalancerIterationLogic: Dict[str, Dict] = {
    "elb": {"ResultName": "LoadBalancerDescriptions"},
    "elbv2": {"ResultName": "LoadBalancers"}
}

exposed_lbs_by_region: dict = {}

# collect exposed security groups
client = boto3.client('ec2', region_name=DEFAULT_AWS_REGION)
aws_regions: List[str] = [region['RegionName'] for region in client.describe_regions()['Regions']]

for region in aws_regions:
    client = boto3.client('ec2', region_name=region)
    print("Start working on region: {0}".format(region))
    response = client.describe_security_groups(Filters=[{'Name': 'ip-permission.cidr', 'Values': ['0.0.0.0/0']}])
    results = response["SecurityGroups"]
    while "NextToken" in response:
        response = client.describe_security_groups(NextToken=response["NextToken"])
        results.extend(response["SecurityGroups"])
    # end collecting security groups

    exposed_security_group_ids: set = {sg["GroupId"] for sg in results}

    # collecting LBs
    lb_to_validate = []
    internet_facing_load_balancers: dict = {}
    for elb_type_name, elb_type_details in LoadBalancerIterationLogic.items():
        client = boto3.client(elb_type_name, region_name=region)
        response = client.describe_load_balancers()
        results = response[elb_type_details["ResultName"]]
        while "NextToken" in response:
            response = client.describe_load_balancers(NextToken=response["NextToken"])
            results.extend(response[elb_type_details["ResultName"]])

        if results:
            lb_to_validate.extend(results)

    print("There are {0} load balancers in the `{1}` region".format(len(lb_to_validate),region))
    for lb in lb_to_validate:
        if lb["Scheme"] == INTERNET_FACING:
            if "SecurityGroups" in lb.keys():
                lb_security_groups: set = set(lb["SecurityGroups"])
                mutual_exposed_sg_for_lb: set = lb_security_groups.intersection(exposed_security_group_ids)
                if mutual_exposed_sg_for_lb:
                    internet_facing_load_balancers.update({lb["LoadBalancerName"]: {
                        "SecurityGroups": list(lb_security_groups)}})

    if internet_facing_load_balancers:
        exposed_lbs_by_region.update({region: internet_facing_load_balancers})

        
# here once the exposed_lbs_by_region is updated, we can decide to do whatever action we want
print(json.dumps(exposed_lbs_by_region, indent=3))
