#!/bin/bash

echo "ID#, #Reviewed" > Reviewed_Counts.csv
psql catmaid catmaid_user -t -A -F "," -c " 
SELECT skeleton_id, COUNT(*) AS \"Reviewed Nodes\" FROM treenode WHERE reviewer_id <> -1 AND project_id = 9 GROUP BY skeleton_id ORDER BY skeleton_id;" >> Reviewed_Counts.csv
echo "ID#, #Unreviewed" > Unreviewed_Counts.csv
psql catmaid catmaid_user -t -A -F "," -c "
SELECT skeleton_id, COUNT(*) AS \"Unreviewed Nodes\" FROM treenode WHERE reviewer_id = -1 AND project_id = 9 GROUP BY skeleton_id ORDER BY skeleton_id;" >> Unreviewed_Counts.csv
echo "ID#, Total # of Nodes" > Total_Counts.csv
psql catmaid catmaid_user -t -A -F "," -c "
SELECT skeleton_id, COUNT(*) AS \"Total Nodes\" FROM treenode WHERE project_id = 9 GROUP BY skeleton_id ORDER BY skeleton_id;" >> Total_Counts.csv
