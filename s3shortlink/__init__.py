import argparse
import boto3
import mimetypes
import sys

from pathlib import Path
from urllib.parse import urlparse

import html_templating
import naming


# pattern adapted from https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html
# TODO: each of the commands which deals with existing data should accept either a name or contents
# as a predicate.
class S3ShortlinkInvoker:

    def __init__(self):
        '''Class-based argument parser.'''
        description = 'Simple self-hosted shortlinking service cmdlet on Amazon S3'
        self.config_description = 'Get, set, and unset configuration settings'
        self.create_description = 'Create a new shortlink'
        self.delete_description = 'Delete an existing shortlink'
        self.modify_description = 'Modify the destination of an existing shortlink'
        self.list_description = 'List all shortlinks in a bucket'
        usage = f'''s3shortlink <command> [<args>]

Create and manage statically hosted shortlinks on an Amazon S3 bucket.
Available subcommands:
    config      {self.config_description}
    create      {self.create_description}
    delete      {self.delete_description}
    modify      {self.modify_description}
    list        {self.list_description}
'''
        # reflection causes more problems than it solves, so avoid it
        subcommand_functions = {
            'config': self.config,
            'create': self.create,
            'delete': self.delete,
            'modify': self.modify,
            'list': self.list,
        }

        parser = argparse.ArgumentParser(description=description, usage=usage)
        parser.add_argument('command', help='Subcommand to run')
        args = parser.parse_args(sys.argv[1:2])

        if args.command not in subcommand_functions:
            print('Unrecognized or missing subcommand')
            parser.print_help()
            exit(1)

        subcommand_functions[args.command]()

    def _generate_crud_parser(self, description, usage=None):
        '''Scaffold a parser for CRUD operations, which require bucket ID.'''
        parser = argparse.ArgumentParser(description=description, usage=usage)
        parser.add_argument(
            '-b',
            '--bucket',
            help='Bucket name on Amazon S3 to use for CRUD operation',
            required=True)

        return parser

    def config(self):
        '''Entry point for config subcommand.'''
        parser = argparse.ArgumentParser(description=self.config_description)
        parser.add_argument('-u',
                            '--unset',
                            action='store_true',
                            help='Flag to be passed to unset an option')
        parser.add_argument(
            'option_name',
            help='Name of configuration option to get/set/unset')
        parser.add_argument(
            'option_value',
            nargs='?',
            help='New value for configuration option; omit to get current value'
        )
        parser.parse_args(sys.argv[2:])

    def create(self):
        '''Entry point for create subcommand.'''
        parser = self._generate_crud_parser(self.create_description)
        name_gen_method = parser.add_mutually_exclusive_group(required=False)
        # TODO allow the coded charset/mnemonic lexicon to be specified on the command line
        # by feeding in the appropriate file name
        name_gen_method.add_argument(
            '-c',
            '--coded',
            action='store_true',
            help='Generate shortlink name using coded, alphanumeric style')
        name_gen_method.add_argument('-n',
                                     '--name',
                                     help='Give shortlink a name manually')
        name_gen_method.add_argument(
            '-m',
            '--mnemonic',
            action='store_true',
            help=
            'Generate shortlink name as a mnemonic, using human-readable words'
        )
        parser.add_argument(
            'target',
            help=
            'Content at the generated shortlink, either a URL or a local file')
        parser.add_argument(
            '--force_weblink',
            action='store_true',
            help=
            'Force creation of a weblink even if the given target looks like a filename on disk.',
            default=False,
            required=False)
        args = parser.parse_args(sys.argv[2:])

        name = self.infer_link_name(args)
        self.create_shortlink(args.bucket, name, target, args.force_weblink)

    def delete(self):
        '''Entry point for delete subcommand.'''
        parser = self._generate_crud_parser(self.delete_description)
        parser.add_argument('shortlink_name',
                            help='Name of the shortlink to be removed')
        parser.parse_args(sys.argv[2:])

    def modify(self):
        '''Entry point for modify subcommand.'''
        parser = self._generate_crud_parser(self.modify_description)
        parser.add_argument(
            'shortlink_name',
            help='Name of the original shortlink to be changed')
        parser.add_argument(
            'target',
            help=
            'New content at the original shortlink, either a URL or a local file'
        )
        parser.add_argument(
            '--force_weblink',
            action='store_true',
            help=
            'Force pointing to a weblink even if the given target looks like a filename on disk.'
        )
        parser.parse_args(sys.argv[2:])

    def list(self):
        '''Entry point for list subcommand.'''
        parser = self._generate_crud_parser(self.list_description)
        parser.parse_args(sys.argv[2:])

    def infer_link_name(self, create_args):
        if create_args.name:
            return create_args.name
        elif create_args.coded:
            return naming.generate_coded_path()
        return naming.generate_mnemonic_path()

    def create_shortlink(self, bucket, name, target, force_weblink):
        s3 = boto3.resource('s3')
        shortlink_object = s3.Object(bucket, name)

        target_path = Path(target)
        treat_as_file = target_path.is_file() and not force_weblink
        normalized_url = None if treat_as_file else urlparse(
            target, scheme='https').geturl()
        metadata = {
            's3shortlink_generated': 'True',
            's3shortlink_build_label': '0.0.1',
            's3shortlink_type':
            'self_hosted_file' if treat_as_file else 'weblink',
        }
        if not treat_as_file:
            metadata['s3shortlink_target'] = normalized_url
        shortlink_object.put(Body=target_path.open() if treat_as_file else
                             html_templating.get_redirect_page(normalized_url),
                             ContentType=mimetypes.guess_type(target_path)
                             if treat_as_file else 'text/html',
                             Metadata=metadata)


if __name__ == '__main__':
    S3ShortlinkInvoker()
