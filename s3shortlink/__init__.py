#!/usr/bin/python3

import argparse
import boto3
import ipaddress
import os
import random
import sqlite3
import sys

import constants
# import link_create, link_list, link_modify, link_delete


def gen_linkname_imgur():
    return ''.join(random.sample(constants.lowercase_alphanumerics, 6))


def gen_linkname_gfycat():
    base = ''
    base += append(random.choice(constants.adjectives).title())
    base += append(random.choice(constants.adjectives).title())
    base += append(random.choice(constants.animals).title())
    return base


def validate_bucket_name(name):
    if len(name) < 3 or len(name) > 63:
        return False
    if not (islower(name[0]) or isnumeric(name[0])):
        return False
    if any(x not in constants.valid_bucket_characters for x in name):
        return False
    if '..' in name or '-.' in name or '.-' in name:
        return False
    if name[-1] == '-':
        return False
    try:
        ipaddress.ip_address(name)
        return False
    except ValueError:
        pass
    return True


def get_aws_keys(cur):
    cur.execute("SELECT * FROM access_data")
    credentials = cur.fetchall()
    if not credentials:
        print("No credentials found for Amazon Web Services.")
        access_key = ""
        secret_key = ""

        while len(access_key) != 20:
            access_key = input("Please enter a valid access key: ")
            if len(access_key) != 20:
                print("Invalid access key, does not have length 20.")

        while len(secret_key) != 40:
            secret_key = input("Please enter a valid secret key: ")
            if len(secret_key) != 40:
                print("Invalid secret key, does not have length 40.")

        cur.execute("INSERT INTO access_data VALUES (?, ?)", (access_key, secret_key))
    else:
        return credentials[0]


def get_bucket_name(cur):
    cur.execute("SELECT * FROM buckets")
    buckets = cur.fetchall()
    final_bucket = None
    if not buckets:
        print("No buckets found on Amazon Web Services.")
        default_bucket_name = "shortlink-" + gen_linkname_imgur()
        custom_bucket_name = "-"

        while not validate_bucket_name(custom_bucket_name):
            custom_bucket_name = input(f"Input a bucket name to use, or just press Enter for the default: {default_bucket_name}")
            if custom_bucket_name == "":
                break
            if not validate_bucket_name(custom_bucket_name):
                print("Invalid bucket name.")

        bucket_name = None
        if custom_bucket_name != "":
            bucket_name = custom_bucket_name
        else:
            bucket_name = default_bucket_name
        cur.execute("INSERT INTO buckets VALUES (?)", (bucket_name))
        final_bucket = bucket_name

    elif len(buckets) > 1:
        print("Multiple buckets found in the database.")
        print("Available buckets for shortlinking are: ")
        for index, bucket in enumerate(buckets):
            print(f"\t{index + 1}. {bucket}")
        index = None

        while index not in range(1, len(buckets) + 1):
            try:
                index = int(input("Please enter the index of the bucket to use."))
            except ValueError:
                pass
            if index not in range(1, len(buckets) + 1):
                print("Invalid bucket index.")
        final_bucket = buckets[index - 1]

    else:
        final_bucket = buckets[0]

    return final_bucket


def main():
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), 's3shortlink.db'))
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS access_data
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                access_key CHAR(20),
                secret_key CHAR(40));""")

    cur.execute("""CREATE TABLE IF NOT EXISTS buckets
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                bucket_id CHAR(16));""")

    conn.commit()

    parser = argparse.ArgumentParser(description="Simple shortlinking service on Amazon S3.")
    subparsers = parser.add_subparsers(help='Functions')
    parser.add_argument('--bucket', help='Manually select which Amazon S3 bucket to act upon.', default=None)

    create_parser = subparsers.add_parser('create', help='Create a new shortlink')
    create_parser.add_argument('url')
    create_parser.add_argument('--gen_method', choices=['imgur', 'gfycat'], default='imgur')
    create_parser.add_argument('--link_name', default=None)
    create_parser.set_defaults(create=True)

    list_parser = subparsers.add_parser('list', help='List all existing shortlinks')
    list_parser.add_argument('search_type', choices=['name', 'url'])
    list_parser.add_argument('query')
    list_parser.set_defaults(list=True)

    modify_parser = subparsers.add_parser('modify', help='Edit an existing shortlink')
    modify_parser.add_argument('search_type', choices=['name', 'url'])
    modify_parser.add_argument('query')
    modify_parser.add_argument('new_value')
    modify_parser.set_defaults(modify=True)

    delete_parser = subparsers.add_parser('delete', help='Remove an existing shortlink')
    delete_parser.add_argument('search_type', choices=['name', 'url'])
    delete_parser.add_argument('query')
    delete_parser.set_defaults(delete=True)

    args = parser.parse_args()
    bucket_name = args.bucket

    if args.create and args.gen_method and args.link_name:
        print("Cannot specify both --gen_method and --link_name.")
        sys.exit(parser.print_help())

    access, secret = get_aws_keys(cur)
    if not bucket_name:
        bucket_name = get_bucket_name(cur)

    # if args.create:
    #     shortlink_create(args)
    # elif args.list:
    #     shortlink_list(args)
    # elif args.modify:
    #     shortlink_modify(args)
    # elif args.delete:
    #     shortlink_delete(args)


if __name__ == '__main__':
    main()
