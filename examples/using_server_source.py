import catmaid

# first intialize a connection object to be used as your skeleton_source
c = catmaid.connection.Connection('server'
                                  'username',
                                  'password'
                                  'project_id')

# initialize a source based on the connection object
src = catmaid.source.get_source(arg=c, cache=True, old_version=True)
# source.get_source(arg) returns a source based on what the argument is
# arg:
#    connection.Conncetion object, a ServerSource is returned
#    directory name, a FileSource is returned.
# cache:
#    boolean value, True allows the Source to save each skeleton loaded under
#    Source.saved_skels or Source.saved_neurons. False creates a Source that
#    does not store values, only returns skeletons/neurons, new each time.
# old_version:
#    boolean value, True converts all skeletons into dictionary form as if the
#    are from catmaid1, this allows all algorithms used on catmaid1 to be run
#    on these skeletons.

# get all skeleton_ids
skeleton_ids = src.skeleton_ids()


# preform operation on all skeletons and save them
def skel_op(skeleton):
    '''Example operation on skeleton'''
    print skeleton['id']

for skeleton in src.all_skeletons_iter():
    '''src.all_skeletons_iter iterates through each skeleton'''
    skel_op(skeleton)  # do the operation on each skeleton
    src.save_skel(skeleton, path='~/Documents/Skeletons')
    # saves all skeletons to specified path, if path is not specified,
    # it will make a 'Skeletons' folder in current working directory

# preform operation on each neuron from a select list
import random
# select 15 random skeleton_ids
select_skeleton_ids = random.sample(skeleton_ids, 15)


def nron_op(neuron):
    '''Example operation on single Neuron'''
    print len(neuron.axons)

for neuron in src.neurons_from_sk_list(select_skeleton_ids):
    nron_op(neuron)
# because src has cache=True now any operations including the neurons on
# select_skeleton_ids list will be faster because they are already cached
# inside src
