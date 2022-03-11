#!/bin/bash

#################### run the next cmd to make it work ####################
#################### chmod +x exposed-sgs.sh & ./exposed-sgs.sh ##########

out='{}'

for region in `aws ec2 describe-regions --region us-east-1 --output text | cut -f4`
do
	
	res=`aws ec2 describe-security-groups --group-ids \
	 --region=$region $(aws ec2 describe-instances --instance-id $id \
	  --query "Reservations[].Instances[].SecurityGroups[].GroupId[]" --filters \
	   Name=instance-state-name,Values=running --region=$region --output text) \
	   --filter Name=ip-permission.protocol,Values=-1 Name=ip-permission.cidr,Values='0.0.0.0/0' \
	    --query "SecurityGroups[*].{Name:GroupName,ID:GroupId}" --output json`
	if [[ ! -z "$res" ]]; then
		out=`echo $out | jq --arg value "$res" --arg region_name "$region" '. + {region: $value}'`
		out=`sed "s/region/$region/g" <<< $out`
	fi
	
done

echo "All regions and exposed security groups\n\n"
echo $out | jq -r
