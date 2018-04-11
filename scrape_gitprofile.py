#!/usr/bin:env python
from __future__ import print_function
import numpy as np
import argparse
import requests
import datetime


def parse_inputs():
    """
    Parses the command line input arguments.


    Parameters
    ----------

    None.

    Returns
    ----------

    args: Dictionary.  Required.
        Dictionary of arguments from the ``argparse`` package.
        Dictionary is keyed by the argument name (e.g., args['username']).
    """

    parser = argparse.ArgumentParser()

    parser.add_argument("-u", "--username", dest="username",
                        help="Github username. Required")

    args = parser.parse_args()

    # We require an input file and an output one.
    if args.username is None: 
        print("Require a username to be specified.")
        parser.print_help()
        raise ValueError 

    return vars(args)


def scrape_profile(args):

    url = "https://github.com/{0}".format(args["username"])
    r = requests.get(url)
    if r.status_code != 200:
        print("Encountered error while fetching webpage {0}".format(url))
        raise RuntimeError
    data = r.text

    commits = np.zeros((7))

    for count, word in enumerate(data.split()):
        if "data-date" in word:
            date = ""
            for letter in word:
                if letter.isdigit():
                    date = date + letter

            if 'first_commit' not in locals():
                first_commit = datetime.datetime.strptime(date, "%Y%m%d") 

            for letter in list(data.split()[count - 1]):
                if letter.isdigit():
                    number_commits = int(letter)
                    break
       
            date = datetime.datetime.strptime(date, "%Y%m%d").weekday()

            commits[date] += number_commits

    print("In total there were {0} commits from {1}".format(sum(commits), first_commit)) 
    print(commits)
                  

if __name__ == '__main__':

    args = parse_inputs()    
    scrape_profile(args)
