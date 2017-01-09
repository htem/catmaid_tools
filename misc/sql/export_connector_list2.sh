#!/bin/bash

#psql catmaid catmaid_user -F , --no-align -c "
#SELECT ct.id, prt.source, pot.target, ct.location FROM
#(SELECT id, location FROM connector WHERE project_id = 9) ct
#JOIN (SELECT connector_id, skeleton_id as source FROM treenode_connector
#  WHERE project_id = 9 AND relation_id = (SELECT id FROM relation WHERE project_id = 9 and relation_name = 'presynaptic_to')) prt
#    ON (ct.id = prt.source)
#JOIN (SELECT connector_id, skeleton_id as target FROM treenode_connector
#  WHERE project_id = 9 AND relation_id = (SELECT id FROM relation WHERE project_id = 9 and relation_name = 'postsynaptic_to')) pot
#ON (ct.id = pot.target)
#" > connectors.csv

echo "#id,source,target,location_x,location_y,location_z" > connectors2.csv
psql catmaid catmaid_user -t -A -F "," -c "
SELECT ct.id, nt.source, nt.target, ct.location_x, ct.location_y, ct.location_z FROM
((SELECT connector_id as source_connector_id, skeleton_id as source FROM treenode_connector
  WHERE project_id = 6 AND relation_id = (SELECT id FROM relation WHERE project_id = 6 and relation_name = 'presynaptic_to')) AS prt
FULL OUTER JOIN (SELECT connector_id as target_connector_id, skeleton_id as target FROM treenode_connector
  WHERE project_id = 6 AND relation_id = (SELECT id FROM relation WHERE project_id = 6 and relation_name = 'postsynaptic_to')) AS pot
    ON (prt.source_connector_id = pot.target_connector_id)) AS nt
JOIN (SELECT id, location_x, location_y, location_z FROM connector WHERE project_id = 6) ct
    ON (nt.source_connector_id = ct.id)
" | sort >> connectors2.csv
