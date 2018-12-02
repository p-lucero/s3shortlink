#!/usr/bin/python3

# TODO set a special metadata bit `s3shortlink` and only operate on things that have this metadata bit
# TODO functionalize more of this and split it out into more files semantically
# TODO make this less kludge

import argparse
import ipaddress
import os
import random
import sqlite3
import sys
import validators

from boto.s3.connection import S3Connection
from boto.s3.key import Key

import constants


def gen_linkname_imgur():
    return ''.join(random.sample(constants.lowercase_alphanumerics, 6))


def gen_linkname_gfycat():
    base = ''
    base += random.choice(constants.adjectives).title()
    base += random.choice(constants.adjectives).title()
    base += random.choice(constants.animals).title()
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

        cur.execute("INSERT INTO access_data (access_key, secret_key) VALUES (?, ?)", (access_key, secret_key))

        return access_key, secret_key
    else:
        return (credentials[0][1], credentials[0][2])


def get_bucket_name(cur):
    cur.execute("SELECT * FROM buckets")
    buckets = cur.fetchall()
    final_bucket = None
    create_required = False
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
        cur.execute("INSERT INTO buckets (bucket_id) VALUES (?)", (bucket_name,))
        final_bucket = bucket_name
        create_required = True

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
        final_bucket = buckets[index - 1][1]

    else:
        final_bucket = buckets[0][1]

    return final_bucket, create_required


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
    parser.set_defaults(create=False, list=False, modify=False, delete=False)
    subparsers = parser.add_subparsers(help='Functions')
    parser.add_argument('--bucket', help='Manually select which Amazon S3 bucket to act upon.', default=None)

    create_parser = subparsers.add_parser('create', help='Create a new shortlink')
    create_parser.add_argument('url')
    create_parser.add_argument('--gen_method', choices=['imgur', 'gfycat'], default='imgur')
    create_parser.add_argument('--link_name', default=None)
    create_parser.set_defaults(create=True)

    list_parser = subparsers.add_parser('list', help='List all existing shortlinks')
    list_parser.add_argument('search_type', choices=['name', 'url'], nargs='?')
    list_parser.add_argument('query', nargs='?')
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

    if all(not x for x in [args.create, args.list, args.modify, args.delete]):
        sys.exit(parser.print_help())

    if args.create and args.gen_method and args.link_name:
        print("Cannot specify both --gen_method and --link_name.")
        sys.exit(parser.print_help())

    access, secret = get_aws_keys(cur)
    if not bucket_name:
        bucket_name, create_required = get_bucket_name(cur)
    conn.commit()

    s3conn = S3Connection(access, secret)

    bucket = None

    if create_required:
        try:
            bucket = s3conn.create_bucket(bucket_name)
        except S3CreateError:
            print("Unable to create bucket on Amazon S3 due to conflict.")
            sys.exit(1)
    else:
        try:
            bucket = s3conn.get_bucket(bucket_name)
        except S3ResponseError:
            print("Unable to access bucket. Maybe it was deleted?")
            sys.exit(1)

    if args.create:
        link_name = None
        if args.link_name:
            link_name = link_name
        elif args.gen_method == 'gfycat':
            link_name = gen_linkname_gfycat()
        else:
            link_name = gen_linkname_imgur()
        if not validators.url(args.url):
            print("Invalid URL provided, cannot create shortlink.")
            sys.exit(1)
        
        k = Key(bucket)
        k.key = link_name
        k.content_type = 'text/html'
        k.set_metadata('url', args.url)
        k.set_contents_from_string(constants.template_HTML.format(args.url, args.url, args.url), policy='public-read')
        print(f"Created shortlink to {args.url} at {constants.s3_basepath.format(bucket_name, link_name)}")

    elif args.list:
        filtering = False
        if args.search_type and not args.query:
            print("Must either specify both search_type and query, or neither (lists all)")
        if args.search_type:
            filtering = True
        keylist = bucket.list()
        filter_type = ""
        if filtering:
            filter_type = f" matching {args.search_type} {args.query}"
        print(f"Shortlinks in bucket {bucket_name}{filter_type}:")

        anyprinted = False
        for key in keylist:
            link_name = key.name
            akey = bucket.get_key(link_name)
            url = akey.get_metadata("url")
            if filtering:
                if args.search_type == "url" and url == args.query:  # FIXME this is a very lazy query method. use regex!!
                    print(f"\t{constants.s3_basepath.format(bucket_name, link_name)} --> {url}")
                    anyprinted = True
                elif args.search_type == "name" and link_name == args.query:
                    print(f"\t{constants.s3_basepath.format(bucket_name, link_name)} --> {url}")
                    anyprinted = True
            else:
                print(f"\t{constants.s3_basepath.format(bucket_name, link_name)} --> {url}")
                anyprinted = True
        if not anyprinted:
            print("\tNo matching shortlinks found.")

    elif args.modify:
        keylist = bucket.list()
        if args.search_type == "url":
            matches = [key for key in keylist if bucket.get_key(key.name).get_metadata("url") == args.query and key.name != args.new_value]
            if len(matches) == 0:
                print("No match found for modify operation.") # TODO make error message more descriptive
            else:
                pass # TODO create a new object
        else:
            matches = [key for key in keylist if key.name == args.query and bucket.get_key(key.name).get_metadata("url") != args.new_value]
            if len(matches) == 0:
                print("No match found for modify operation.") # TODO make error message more descriptive
            else:
                active_shortlink = matches[0]
                active_shortlink.set_metadata('url', args.new_value)
                active_shortlink.set_contents_from_string(constants.template_HTML.format(args.new_value, args.new_value, args.new_value), policy='public-read')
                print(f"Modified link {constants.s3_basepath.format(bucket_name, active_shortlink.name)} to point to {args.new_value}.")

    elif args.delete:
        keylist = bucket.list()
        if args.search_type == "url":
            matches = [key for key in keylist if bucket.get_key(key.name).get_metadata("url") == args.query]
            if not matches:
                print(f"Unable to find a shortlink pointing to {args.query}")
            for match in matches:
                print(f"Deleting shortlink {constants.s3_basepath.format(bucket_name, match.name)} which pointed to {args.query}")
                match.delete()
        else:
            matches = [key for key in keylist if key.name == args.query]
            if len(matches) == 1:
                print(f"Deleting shortlink {constants.s3_basepath.format(bucket_name, matches[0].name)} which pointed to {bucket.get_key(matches[0].name).get_metadata('url')}")
                matches[0].delete()
            elif len(matches) == 0:
                print(f"Unable to find a shortlink with name {args.query}")
            else:
                print("What?")


if __name__ == '__main__':
    main()
