// Thanks to Andrew Champion for providing example
// TODO ideally this script can be made into a js injection for browser addon
//     Currently this script lives in
//       catmaid/django/applications/catmaid/static/js/layers/

/**
 * project ID -> primary stack ID -> stack IDs to open
as overlays.  These are database project and stack ids, but could be queried.
 */
var AUTO_OVERLAYS = {
  1: {
    4: [3]
  }
};

/**
 * when initializing a stackviewer, add any stacks in CUSTOM_AUTOMATIC_OVERLAYS
 * as overlays.
 */
var openAutomaticOverlays = function (stackViewer) {
  var projectId = stackViewer.getProject().getId();
  var primaryStackId = stackViewer.primaryStack.id;

  var projectMap = AUTO_OVERLAYS[projectId];
  if (!projectMap) return;
  var overlays = projectMap[primaryStackId];

  overlays.forEach(function (stackId) {
    openProjectStack(projectId, stackId, undefined, true);
  });
};

// Register listener.
CATMAID.Init.on(CATMAID.Init.EVENT_PROJECT_CHANGED, function (project) {
  project.on(Project.EVENT_STACKVIEW_ADDED, openAutomaticOverlays);
});
