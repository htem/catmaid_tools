#!/bin/bash

# get oldest treenode
#SELECT * FROM treenode WHERE project_id = 9 ORDER BY edition_time DESC LIMIT 1;
PROJECT="9"
START_TIME="2014-01-01"
END_TIME="2014-07-01"

echo "#user stats from $START_TIME to $END_TIME" > user_stats.csv
echo "#username, new, edited, reviewed" >> user_stats.csv
psql catmaid catmaid_user -t -A -F "," -c "
SELECT un1 as username, new_count, edited_count, review_count FROM 
        (((SELECT username as un1, count(user_id) as new_count FROM treenode, auth_user
            WHERE project_id=$PROJECT AND creation_time > '$START_TIME' AND creation_time < '$END_TIME' AND user_id=auth_user.id GROUP BY username) AS nodes_table
    LEFT OUTER JOIN
        (SELECT username as un2, count(editor_id) as edited_count FROM treenode, auth_user
            WHERE project_id=$PROJECT AND edition_time > '$START_TIME' AND edition_time < '$END_TIME' AND editor_id != user_id AND editor_id = auth_user.id GROUP BY username) AS edited_table
    ON un1 = un2) AS t0
    LEFT OUTER JOIN
        (SELECT username as un3, count(reviewer_id) as review_count FROM treenode, auth_user
            WHERE project_id=$PROJECT AND review_time > '$START_TIME' AND review_time < '$END_TIME' AND reviewer_id=auth_user.id GROUP BY username) AS t1
    ON un1 = un3) AS stats_table
" >> user_stats.csv

# get edited nodes TODO filter by date
#echo "#user, edited_nodes"
#SELECT username, count(editor_id) FROM treenode, auth_user WHERE project_id=9 AND editor_id != user_id AND editor_id=auth_user.id GROUP BY username;

# get reviewed nodes TODO filter by date, should there be a reviewer_id != user_id ?
#SELECT username, count(reviewer_id) FROM treenode, auth_user WHERE project_id=9 AND reviewer_id=auth_user.id GROUP BY username

# get created nodes TODO filter by date
#SELECT username, count(user_id) FROM treenode, auth_user WHERE project_id=9 AND user_id=auth_user.id GROUP BY username;


# new and edited filter by date

#SELECT un1 as username, new_count, edited_count FROM ((SELECT username as un1, count(user_id) as new_count FROM treenode, auth_user WHERE project_id=9 AND user_id=auth_user.id GROUP BY username) AS nodes_table LEFT OUTER JOIN (SELECT username as un2, count(editor_id) as edited_count FROM treenode, auth_user WHERE project_id=9 AND editor_id = auth_user.id GROUP BY username) AS edited_table ON un1 = un2) AS stats_table;

# filter by date range
#echo "#user_id, editor_id, reviewer_id" > user_stats.csv
#psql catmaid catmaid_user -t -A -F "," -c "
#SELECT (user_id, editor_id, reviewer_id) FROM treenode WHERE project_id = 9 AND edition_time > '2014-01-01' AND edition_time < '2014-07-01'
#" >> user_stats.csv

#echo "#id, username, first_name, last_name" > users.csv
#psql catmaid catmaid_user -t -A -F "," -c "
#SELECT (id, username, first_name, last_name) FROM auth_users
#" >> users.csv
