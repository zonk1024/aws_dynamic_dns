#!/usr/bin/env python3

import boto3
import requests
import socket
import yaml


def CanNotHazIpException(Exception):
    pass


def get_config():
    with open("config.yaml", "r") as f:
        return yaml.load(f, Loader=yaml.Loader)


def get_public_ip():
    response = requests.get("https://canhazip.com")
    if response.status_code != 200:
        raise CanNotHazIpException("Failed to get public IP")
    return response.text.strip()


def get_route53_client(config):
    return boto3.client(
        "route53",
        aws_access_key_id=config["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=config["AWS_SECRET_ACCESS_KEY"],
    )


def get_current_record(domain):
    try:
        return socket.gethostbyname(domain)
    except Exception as e:
        raise CanNotHazIpException("DNS lookup failed")


def update_records(config):
    public_ip = get_public_ip()
    output = []
    for account in config["ACCOUNTS"]:
        client = get_route53_client(account)
        for record in account["RECORDS"]:
            if public_ip == get_current_record(record["DOMAIN"]):
                output.append("No change needed: {} -> {}".format(record["DOMAIN"], public_ip))
                continue
            try:
                output.append(
                    client.change_resource_record_sets(
                        ChangeBatch={
                            "Changes": [
                                {
                                    "Action": "UPSERT",
                                    "ResourceRecordSet": {
                                        "Name": record["DOMAIN"],
                                        "ResourceRecords": [
                                            {
                                                "Value": public_ip,
                                            },
                                        ],
                                        "TTL": record["TTL"],
                                        "Type": "A",
                                    },
                                },
                            ],
                            "Comment": record["COMMENT"],
                        },
                        HostedZoneId=record["HOSTED_ZONE"],
                    )
                )
            except CanNotHazIpException as e:
                output.append(e)
    return output


def main():
    config = get_config()
    results = update_records(config)
    for result in results:
        print(result)


if __name__ == "__main__":
    main()
