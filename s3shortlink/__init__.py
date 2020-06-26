import argparse
import sys


# pattern adapted from https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html
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
        '''Scaffold a parser for CRUD operations, which require access key, secret key, and bucket ID.'''
        parser = argparse.ArgumentParser(description=description, usage=usage)
        parser.add_argument('-a', '--access', help='Access key to be used in connecting to Amazon S3')
        parser.add_argument('-b', '--bucket', help='Bucket name on Amazon S3 to use for CRUD operation')
        parser.add_argument('-s', '--secret', help='Secret key to be used in connecting to Amazon S3')

        return parser

    def config(self):
        '''Entry point for config subcommand.'''
        parser = argparse.ArgumentParser(description=self.config_description)
        parser.add_argument('-u', '--unset', action='store_true', help='Flag to be passed to unset an option')
        parser.add_argument('option_name', help='Name of configuration option to get/set/unset')
        parser.add_argument('option_value', nargs='?', help='New value for configuration option; omit to get current value')
        parser.parse_args(sys.argv[2:])

    def create(self):
        '''Entry point for create subcommand.'''
        parser = self._generate_crud_parser(self.create_description)
        name_gen_method = parser.add_mutually_exclusive_group(required=False)
        # TODO allow the coded charset/mnemonic lexicon to be specified on the command line
        # by feeding in the appropriate file name

        # TODO allow the user to pass their own template html file as a command line argument
        # in both this method and the modify method
        name_gen_method.add_argument('-c', '--coded', action='store_true', help='Generate shortlink name using coded, alphanumeric style')
        name_gen_method.add_argument('-n', '--name', help='Give shortlink a name manually')
        name_gen_method.add_argument('-m', '--mnemonic', action='store_true', help='Generate shortlink name as a mnemonic, using human-readable words')
        parser.add_argument('long_url', help='URL for the generated shortlink to redirect to')
        parser.parse_args(sys.argv[2:])

    def delete(self):
        '''Entry point for delete subcommand.'''
        parser = self._generate_crud_parser(self.delete_description)
        parser.add_argument('shortlink_name', help='Name of the shortlink to be removed')
        parser.parse_args(sys.argv[2:])

    def modify(self):
        '''Entry point for modify subcommand.'''
        parser = self._generate_crud_parser(self.modify_description)
        parser.add_argument('shortlink_name', help='Name of the original shortlink to be changed')
        parser.add_argument('long_url', help='New destination for the original shortlink')
        parser.parse_args(sys.argv[2:])

    def list(self):
        '''Entry point for list subcommand.'''
        parser = self._generate_crud_parser(self.list_description)
        parser.parse_args(sys.argv[2:])


if __name__ == '__main__':
    S3ShortlinkInvoker()
