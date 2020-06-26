'''Various minor utility methods for s3shortlink.'''
import ipaddress
import random
import re
import string

adjectives_list = open('adjectives.txt').read().split('\n')
animals_list = open('animals.txt').read().split('\n')

# Valid characters to compose an Amazon S3 bucket name
bucket_regex = re.compile(r'^[a-z0-9][a-zA-Z0-9.-]+[a-zA-Z0-9.]$')
punctuation_regex = re.compile(r'[.-]{2}')

default_charset = ''.join((string.ascii_lowercase, string.digits))
default_lexicon = [
    {
        'instances': 2,
        'words': adjectives_list,
    },
    {
        'instances': 1,
        'words': animals_list
    }
]


def generate_coded_path(charset=None, n_chars=6):
    '''Generate a short coded path of gibberish characters.'''
    if charset is None:
        global default_charset
        charset = default_charset

    return ''.join(random.sample(charset, n_chars))


def generate_mnemonic_path(lexicon=None):
    '''
    Generate a mnemonic path, using a lexicon of words.

    The lexicon is a list of dictionaries. Each dictionary should contain two
        keys: `instances`, which specifies how many times to use the
        dictionary, and `words`, which is a list of words to sample from.
    '''
    if lexicon is None:
        global default_lexicon
        lexicon = default_lexicon

    path = ''
    for dictionary in lexicon:
        instances = dictionary['instances']
        words = dictionary['words']

        # only use random.sample if we need to
        if instances > 1:
            path += ''.join(x.title() for x in random.sample(words, instances))
        else:
            path += random.choice(words).title()

    return path


def validate_bucket_name(name):
    '''Return whether the given bucket name is valid for Amazon S3.'''
    if len(name) < 3 or len(name) > 63:
        return False
    if punctuation_regex.match(name) or not bucket_regex.match(name):
        return False

    # IP addresses are not valid bucket names, so we want a ValueError here
    try:
        ipaddress.ip_address(name)
    except ValueError:
        return True
    return False
