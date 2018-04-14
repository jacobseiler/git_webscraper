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
                  

def search_between_inverted_commas(data): 

    word = ""
    inside_commas = False

    for letter in data:
        
        if inside_commas and letter == '"':
            break
        if inside_commas: 
            word = word + letter          
        if letter == '"':
            inside_commas = True

    return word

def get_repos(username, pagenumber=1):
    """
    Gets the list of repo names. 

    If a username has many repositories, the names will be across multiple
    pages. This function checks for this and calls itself iteratively until the
    last page is reached. 

    Parameters
    ----------

    username: String. Required.
        The Github username we are scraping. 

    pagenumber: Integer. Optional.
        The pagenumber we are loading. Used to iterate through to the next
        page.

    Returns
    ----------
   
    repos_list: List of Strings. Required.
        List of repository names for the given pagenumber. 
    """

    repos = []

    url = "https://github.com/{0}".format(username)
    payload = {"page" : pagenumber, "tab" : "repositories"}
    r = requests.get(url, params=payload)
    if r.status_code != 200:
        print("Encountered error while fetching webpage {0}".format(url))
        raise RuntimeError
    data = r.text

    # We need to check if there are multiple pages of repository we needs to
    # account for.  If there are, call the function again with the next page.

    if "pagination" in data: #  Identified there are multiple pages. 
        for count, word in enumerate(data.split()): 
            if "pagination" in word:  #  Go to the line with the page number.
                for i in range(20): 
                # We search around the word 'pagination' to see if the next
                # page is disabled (i.e., we're at the final page). 
                    if "next_page" in data.split()[count+i]:
                        if not "disabled" in data.split()[count+i+1]:
                            # If the next page is enabled, call function again.                    
                            new_repos_list = get_repos(username,
                                                       pagenumber=pagenumber+1)
                
                            # Get rid of nested list structure.
                            for new_repo in new_repos_list:
                                repos.append(new_repo)


    # The repository name is near the word 'codeRepository'. So search for this
    # word and then grab the repository name.

    for count, word in enumerate(data.split()):        
        if "codeRepository" in word:
            at_name = False
            this_repo = ""

            # This line will contain the repository name within inverted commas
            # and also contains the username.  So go through this line, grab
            # the letters between the inverted commas and then cut out the
            # username.

            this_repo = search_between_inverted_commas(data.split()[count-2])

            username_string = "/{0}/".format(username)
            this_repo = this_repo.replace(username_string, "")

            repos.append(this_repo)
    
    return repos


def get_branches(username, reponame):

    url = "https://github.com/{0}/{1}/branches".format(username, reponame)
    branch_names = []

    r = requests.get(url)
    if r.status_code != 200:
        print("Encountered error while fetching webpage {0}".format(url))
        raise RuntimeError
    data = r.text

    for count, word in enumerate(data.split()):
        if "data-branch-name" in word:
            thisbranch_name = search_between_inverted_commas(data.split()[count])
            branch_names.append(thisbranch_name)

        if "Active branches" in word:
            break

    return branch_names


def get_repo_commits(username, reponame, branchname):


    url = "https://github.com/{0}/{1}/commits/{2}".format(username, reponame,
                                                          branchname)
    
    r = requests.get(url)
    if r.status_code != 200:        
        print("Encountered error while fetching webpage {0}".format(url))
        raise RuntimeError
    data = r.text


def scrape_commit_history(args):

    data = {}

    repos_list = get_repos(args["username"])
    for repo in repos_list:
        branches_list = get_branches(args["username"], repo)

        for branch in branches_list:
            print("Scraping branch {0} from repo {1}".format(branch, repo))        
            commits_this_repo = get_repo_commits(args["username"], repo,
                                                 branch) 

if __name__ == '__main__':

    args = parse_inputs()    
    #scrape_profile(args)
    scrape_commit_history(args)
