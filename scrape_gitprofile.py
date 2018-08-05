#!/usr/bin:env python
from __future__ import print_function
import numpy as np
import argparse
import requests
import datetime
import dateutil.parser # Specific parser for ISO 8601 used by Github.


def scrape_profile(username):

    url = "https://github.com/{0}".format(username)
    r = requests.get(url)
    if r.status_code != 200:
        print("Encountered error while fetching webpage {0}".format(url))
        raise RuntimeError
    data = r.text
    data_split = data.split()

    commits = np.zeros((7))

    for count, word in enumerate(data_split):
        if "data-date" in word:
            date = ""
            for letter in word:
                if letter.isdigit():
                    date = date + letter

            if 'first_commit' not in locals():
                first_commit = datetime.datetime.strptime(date, "%Y%m%d") 

            for letter in list(data_split[count - 1]):
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
    data_split = data.split()

    # We need to check if there are multiple pages of repository we needs to
    # account for.  If there are, call the function again with the next page.

    if "pagination" in data: #  Identified there are multiple pages. 
        for count, word in enumerate(data_split): 
            if "pagination" in word:  #  Go to the line with the page number.
                for i in range(20): 
                # We search around the word 'pagination' to see if the next
                # page is disabled (i.e., we're at the final page). 
                    if "next_page" in data_split[count+i]:
                        if not "disabled" in data_split[count+i+1]:
                            # If the next page is enabled, call function again.                    
                            new_repos_list = get_repos(username,
                                                       pagenumber=pagenumber+1)
                
                            # Get rid of nested list structure.
                            for new_repo in new_repos_list:
                                repos.append(new_repo)


    # The repository name is near the word 'codeRepository'. So search for this
    # word and then grab the repository name.

    for count, word in enumerate(data_split):        
        if "codeRepository" in word:
            this_repo = ""

            # This line will contain the repository name within inverted commas
            # and also contains the username.  So go through this line, grab
            # the letters between the inverted commas and then cut out the
            # username.

            this_repo = search_between_inverted_commas(data_split[count-2])

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
    data_split = data.split()

    for count, word in enumerate(data_split):
        if "data-branch-name" in word:
            thisbranch_name = search_between_inverted_commas(data_split[count])
            branch_names.append(thisbranch_name)

        if "Active branches" in word:
            break

    return branch_names



def get_repo_commits(username, reponame, branchname, pagenumber=1):

    commits_this_repo = []
    this_repo_sha = []

    url = "https://github.com/{0}/{1}/commits/{2}".format(username, reponame,
                                                          branchname)

    if pagenumber % 10 == 0:
        print("Oof, this is a big one. On page {0}".format(pagenumber))

    payload = {"page" : pagenumber}     
    r = requests.get(url, params=payload)
    if r.status_code != 200:        
        print("Encountered error while fetching webpage {0}".format(url))
        print("Status code {0}".format(r.status_code))
        raise RuntimeError
    data = r.text

    data_split = data.split()

    # We need to check if there are multiple pages of commits.

    if "pagination" in data: #  Identified there are multiple pages.
        for count, word in enumerate(data_split):
            if "pagination" in word:  #  Go to the line with the page number.
                for i in range(20):
                # We search around the word 'pagination' to see if the next
                # page is disabled (i.e., we're at the final page).
                    if "Older" in data_split[count+i]:
                        if not "disabled" in data_split[count+i]:
                            # If the next page is enabled, call function again.                    
                            new_commits_list, new_commits_sha = get_repo_commits(username,
                                                                                 reponame,
                                                                                 branchname,
                                                                                 pagenumber=pagenumber+1)

                            # Get rid of nested list structure.
                            for new_commit, new_sha in zip(new_commits_list,
                                                           new_commits_sha):
                                commits_this_repo.append(new_commit)
                                this_repo_sha.append(new_sha)

    # We care about the date-times so search for this word.
    # However we need to be careful.  This page contains ALL commits on this
    # branch, including those made by other people.  So we need to ensure that
    # the commit belongs to the specificied user. 

    for count, word in enumerate(data_split):
        if "datetime" in word:
            used_commit = False 
            for i in range(100):

                author_string = "author={0}".format(username)
                commit_string = "/{0}/{1}/commit/".format(username, reponame)

                if author_string in data_split[count-i]: 

                    this_commit = ""

                    # This line will contain the commit datetime within inverted
                    # commas. 

                    this_commit = search_between_inverted_commas(word)

                    commits_this_repo.append(this_commit)
                    used_commit = True 


                if commit_string in data_split[count-i] and used_commit:
                    commit_sha = search_between_inverted_commas(data_split[count-i])
                    commit_sha = commit_sha.replace(commit_string, "") 

                    this_repo_sha.append(commit_sha) 

                    break

 
    return commits_this_repo, this_repo_sha 


def scrape_commit_history(username):

    commits = {}
    sha = {}

    repos_list = get_repos(username)

    for repo in repos_list:

        #if repo != "grid-model":
        #    continue
        if repo == "astropy":
            continue

        commits[repo] = {}
        sha[repo] = {}

        branches_list = get_branches(username, repo)
        
        for branch in branches_list:
            print("Scraping branch {0} from repo {1}".format(branch, repo))        
            commits_this_repo, sha_this_repo = get_repo_commits(username, repo,
                                                                branch) 

            converted_times = []
            for date in commits_this_repo:
                converted_times.append(dateutil.parser.parse(date))

            commits[repo][branch] = converted_times 
            sha[repo][branch] = sha_this_repo 

    return commits, sha 


def summarize_commits(username, commits, sha):

    print("")
    print("================================")
    print("Summarising commit history for {0}".format(username))
    print("================================")
    print("")

    repos = commits.keys() 
    print("There were are total of {0} repositories that "
          "contained commits.".format(len(repos)))

    max_branches_number = 0
    max_commits_number = 0
    max_unique_commits_number = 0

    unique_commits = {}

    for repo in repos:

        max_commits_thisrepo_number = 0

        branches = commits[repo].keys()

        if len(branches) > max_branches_number:
            max_branches_number = len(branches)
            max_branches_repo = repo

        for branch in branches:
           if len(commits[repo][branch]) > max_commits_number:
                max_commits_number = len(commits[repo][branch])
                max_commits_repo = repo
                max_commits_branch = branch 

           if len(commits[repo][branch]) > max_commits_thisrepo_number:
                max_commits_thisrepo_branch = branch
                max_commits_thisrepo_number = len(commits[repo][branch]) 

        max_commits_sha = sha[repo][max_commits_thisrepo_branch] 
        unique_commits[repo] = max_commits_thisrepo_number

        for branch in branches: 
            if branch == max_commits_thisrepo_branch:
                continue


            repeated_sha = np.intersect1d(max_commits_sha,
                                          sha[repo][branch])

            new_commits = len(sha[repo][branch]) - len(repeated_sha)
            unique_commits[repo] += new_commits

    print("The repository with the most branches is {0} with " 
          "{1} branches".format(max_branches_repo, max_branches_number))

    print("The repository with the most commits is {0} with "
          "{1} commits on branch {2}".format(max_commits_repo,
                                             max_commits_number,
                                             max_commits_branch)) 

    max_unique_commits = max(unique_commits, key=unique_commits.get)
    print("The repository with the most UNIQUE commits is {0} with "
          "{1} commits".format(max_unique_commits,
                               max(unique_commits.values())))                              

    print("Across all repositories, there are {0} unique " 
          "commits.".format(sum(unique_commits.values())))


if __name__ == '__main__':


    username="manodeep"

    commits, sha = scrape_commit_history(username)    

    summarize_commits(username, commits, sha)
