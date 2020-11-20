#!/usr/bin/python
#
# List jira issues in the Linux terminal
#
# 2020 :: Erik
# 20200310 :: Tim - Add group by sprint

import os
import sys
import jira
import json
import re
from terminaltables import SingleTable
from colorclass import Color, Windows

try:
    API_USER = os.environ['JIRA_API_USER']
    API_TOKEN = os.environ['JIRA_API_TOKEN']
    API_URL = 'https://employer.atlassian.net'
except Exception as e:
    print """

        OOPS: looks like you forgot something!

        Set (or export) the following env variables:

            JIRA_API_USER  .......  This is your email address
            JIRA_API_TOKEN  ......  This can be generated from 
                                    account settings -> security -> manage api tokens

        call me with:

            JIRA_API_USER=chookity.pok@boop.the.snoot JIRA_API_TOKEN=chookitypokboopthesnoot ./jiracli.py <arg1> .. <argN>

        Protip, you probably want to alias this in your shellrc:

            alias jira='JIRA_API_USER=fgs.fgs@foo.bar JIRA_API_TOKEN=blorp /path/to/jiracli.py'

        Currently supported args:

            --team   .............  Include issues for the whole team
            --active  ............  Filter out issues with 'inactive' statuses or group by active sprints with --sprint option
            --inactive  ..........  Filter out issues with 'active' statuses or group by inactive sprints with --sprint option
            --sprint  ............  Group issues by 'sprint'.

    """
    sys.exit(1)


# need to be doulbequoted
PROJECT_FILTER = [
    '"ABC"',
    '"CDE"',
    '"EFG"',
];

# need to be doublequoted
TEAM_FILTER = [
    '"boopity.snoot@employer.com"',
    '"chookity.pok@employer.com"'
];

ACTIVE_STATUSES = [
    'In Progress',
    'Review',
    'In Review',
    'Selected for Development',
    'Pending'
]

# the rest of the statuses will be
# populated here, and sorted between
# 'active' and 'inactive' statuses.
#
# todo: find a better way to sort issues
#
UNKNOWN_STATUSES = []

INACTIVE_STATUSES = [
    'Backlog',
    'Done',
    'Completed',
    'Closed',
    'Canceled',
    'Declined'
]

INACTIVE_SPRINT_STATUSES = [
    'CLOSED'
]


def issues_for(jira=None, usernames=["currentuser()"], projects=["DOESNOTEXIST"]):
    if not jira:
        return {}
    jql = 'assignee in ({}) and project in ({})'.format(
        ','.join(usernames),
        ','.join(projects))
    issues = []
    block_idx = 0;
    block_size = 50;
    while True:
        issue_block = jira.search_issues(jql,
            startAt=block_idx * block_size,
            maxResults=block_size)
        block_idx = block_idx + 1
        for issue in issue_block:
            if issue.fields.status.name not in (ACTIVE_STATUSES + INACTIVE_STATUSES + UNKNOWN_STATUSES):
        	UNKNOWN_STATUSES.append(issue.fields.status.name);
            issues.append(issue);
        if len(issue_block) == 0:
            break
    return issues;


def sort_issues(l_issues):
    status_sort = ACTIVE_STATUSES + UNKNOWN_STATUSES + INACTIVE_STATUSES;
    priosz = lambda x: status_sort.index(x.fields.status.name) if x.fields.status.name in status_sort else -1
    swap = True;
    while swap:
        swap = False
        for i in range(0, len(l_issues)-1):
            left = l_issues[i]
            right = l_issues[i+1]
            if priosz(left) > priosz(right):
        	    l_issues[i] = right
        	    l_issues[i+1] = left
        	    swap = True
    return l_issues


def group_issues(l_issues):
    d_issues = {}
    for issue in l_issues:
        group_by_keys = []
        assignee = str(issue.fields.assignee);
        orig_assignee = assignee
        if '--sprint' in sys.argv:
            if '--team' in sys.argv:
                assignee = 'Team'
            sprint_info_list = getattr(issue.fields(), 'customfield_10002')
            if isinstance(sprint_info_list, list):
                for sprint_info in sprint_info_list:
                    sprint_name = re.findall(r"name=[^,]*", str(sprint_info))
                    sprint_name = re.sub("name=", "", "," . join(sprint_name))
                    sprint_state = re.findall(r"state=[^,]*", str(sprint_info))
                    sprint_state = re.sub("state=", "", "," . join(sprint_state))
                    in_active_sprint = (sprint_state not in (INACTIVE_SPRINT_STATUSES))
                    if (in_active_sprint and '--active' in sys.argv) or (not in_active_sprint and '--inactive' in sys.argv) or (not '--inactive' in sys.argv and not '--active' in sys.argv):
                        group_by_keys.append(sprint_name)
            else:
                if issue.fields.status.name not in (INACTIVE_STATUSES):
                    group_by_keys.append('*ACTIVE* but not in a Sprint')
        else:
            group_by_keys.append(str(issue.fields.project))
        for group_key in group_by_keys:
            if not group_key in d_issues:
                d_issues[group_key] = {}
            if not assignee in d_issues[group_key]:
                d_issues[group_key][assignee] = [];
            issue.fields.assignee = orig_assignee
            d_issues[group_key][assignee].append(issue);

    return d_issues;
    

jira = jira.JIRA(API_URL, basic_auth=(API_USER, API_TOKEN))
l_issues = [];

# args filters start here

opt_usernames = ['currentuser()']
opt_projects=PROJECT_FILTER

if '--team' in sys.argv:
    opt_usernames=TEAM_FILTER

l_issues = issues_for(
    jira=jira,
    usernames=opt_usernames,
    projects=opt_projects);

if '--active' in sys.argv:
    l_issues = [x for x in l_issues if x.fields.status.name not in INACTIVE_STATUSES]

if '--inactive' in sys.argv:
    l_issues = [x for x in l_issues if x.fields.status.name not in ACTIVE_STATUSES]

if ('--team' in sys.argv and '--sprint' in sys.argv): 
    issue_rep = lambda x : (
        x.fields.status.name[0:15],
        x.fields.summary[0:40],
        x.fields.assignee[0:40],
        API_URL + "/browse/" + x.key)
else:
    issue_rep = lambda x : (
        x.fields.status.name[0:15],
        x.fields.summary[0:40],
        API_URL + "/browse/" + x.key)

# args filters end here

g_issues = group_issues(l_issues);

for group_key in g_issues:
    for assignee in g_issues[group_key]:
        table_data = sort_issues(g_issues[group_key][assignee]);
        table_data = map(issue_rep, table_data);
        single_table = SingleTable(table_data, Color('{autored}'+group_key+" / "+assignee+"{/autored}"))
        single_table.inner_heading_row_border = False;
        print single_table.table;
