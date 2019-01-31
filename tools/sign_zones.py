"""
sign zone with new keys
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import dns.zone
import keytag


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parseargs():
    """
    Parse arguments of the script

    Return:
        key_json (str)  path to file with info about replacing keys
        key_dir (str)   path to the directory with the keys
        zone (str)      path to zonefile
    """
    argparser = argparse.ArgumentParser()
    argparser.add_argument("key_json",
                           help="path to file with with info about replacing keys")
    argparser.add_argument("zone",
                           help="path to zonefile")
    argparser.add_argument("-d", "--key_dir",
                           help="""path to the directory where the keys are stored,
                           default is working directory""", default=".")
    args = argparser.parse_args()

    if not os.path.isfile(args.key_json):
        logger.error("%s is not a file.", args.key_json)
        sys.exit(1)
    if not os.path.isfile(args.zone):
        logger.error("%s is not a file.", args.zone)
        sys.exit(1)
    if not os.path.isdir(args.key_dir):
        logger.error("%s is not a directory.", args.key_dir)
        sys.exit(1)
    if not args.zone.endswith(".zone"):
        logger.error("%s does not have the standart zonefile name format.", args.zone)
        sys.exit(1)
    return args.key_json, args.key_dir, args.zone


def remove_dnskeys(zonefile, keys):
    """
    Remove DNSKEYs from zonefile

    Attributes:
        zonefile (str)      path to zonefile
        keys (set of int)   set of key tags  to remove
    """
    origin = dns.name.from_text(zonefile.split("/")[-1][:-5])
    zone = dns.zone.from_file(zonefile, origin=origin, relativize=False)
    dnskeys = zone.get_rdataset(origin, dns.rdatatype.DNSKEY, create=True)
    for key in dnskeys:
        if keytag.from_dnskey(key) in keys:
            dnskeys.remove(key)
    zone.to_file(zonefile, relativize=False)


def include_keys(zone, keys):
    """
    Include keys to a zone

    Attributes:
        zone (str)          path to zonefile
        keys (list of str)  names of keyfiles
    """
    with open(zone, "a+") as zonefile:
        for key in keys:
            with open(key) as keyfile:
                zonefile.write(keyfile.read())


def sign_zone(zone, key_dir):
    """
    Sign a zone

    Attributes:
        zone (str)          path to zonefile
        key_dir (str)       path to directory to find key files
    """
    zonename = zone.split("/")[-1][:-5]
    command = ["dnssec-signzone", "-z", "-N", "KEEP", "-O", "full", "-P",
               "-K", key_dir, "-d", key_dir, "-o", zonename, zone]
    # TODO pokud chceme v zone NSEC3 záznamy, potřebuje signzone další parametry
    print(" ".join(command))
    if subprocess.call(command) != 0:
        logger.error("Cannot sign zone")
        sys.exit(1)


def main():
    """
    sign zone with new keys
    """
    key_json, key_dir, zone = parseargs()
    with open(key_json) as key_file:
        keys = json.load(key_file)
    remove_dnskeys(zone, {key["old"] for key in keys})
    include_keys(zone, [key_dir + "/" + key["file"] for key in keys])
    sign_zone(zone, key_dir)


main()