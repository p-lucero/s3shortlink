#!/usr/bin/python3

import argparse
import boto3
import ipaddress
import random
import sqlite3
import sys

import constants


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
    if not buckets:
        print("No buckets found on Amazon Web Services.")
        default_bucket_name = "shortlink-" + ''.join(random.sample(constants.lowercase_alphanumerics, 6))
        custom_bucket_name = "-"
        while not validate_bucket_name(custom_bucket_name):
            custom_bucket_name = input(f"Input a bucket name to use, or just press Enter for the default: {default_bucket_name}")
            if custom_bucket_name == "":
                break
            if not validate_bucket_name(custom_bucket_name):
                print("Invalid bucket name.")


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
    parser.add_argument('cmd', metavar='cmd', type=str, nargs=1, help='Command type (one of create, list, edit, or delete)')
    # parser.add_argument('') # TODO more stuff here
    args = parser.parse_args()

    if args.cmd not in constants.valid_cmds:
        sys.exit(parser.print_help())

    access, secret = get_aws_keys(cur)
    bucket_name = get_bucket_name(cur)

    if args.cmd == 'create':
        pass
    elif args.cmd == 'list':
        pass
    elif args.cmd == 'delete':
        pass
    elif args.cmd == 'modify':
        pass


if __name__ == '__main__':
    main()
