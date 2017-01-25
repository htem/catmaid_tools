Description:
- blender_import : import catmaid skeletons into blender
- catmaid.py : access script for catmaid data (adjacency matrix, skeleton data, etc...)

# Contributors

* [Brett Graham](https://github.com/braingram)
* [Brendan Shanny](https://github.com/brenshanny)
* [Russel Torres](https://github.com/RussTorres)
* [Logan Thomas](https://github.com/Lathomas42)
* [Rui Zheng](https://github.com/rui14)

## Description

A python package used for pulling and analyzing data from [Catmaid](www.catmaid.org)

## Installation

Download the [source code (ZIP)](https://github.com/htem/catmaid_tools/archive/module.zip "catmaid_tools source code") and then run:
```python
    python setup.py install
```
You may need to run this command with 'sudo'

## Uses

####Basic skeleton and Neuron retreival/saving
To import skeletons or neurons from a catmaid server simply run the following:
```python
import catmaid

source = catmaid.get_source()
```
The `catmaid.get_source()` command with no arguments attempts to call on environment variables for a server, project, user, and password. If these variables do not exist it prompts for input for each one. These environment variables can be set by adding the following lines to your ~/.bashrc file.
```
    export CATMAID_SERVER="http://catmaid.your.server"
    export CATMAID_PROJECT="Your_Project_Name"
    export CATMAID_USER="YourUserName"
    export CATMAID_PASSWORD="yourpassword"
```
Once `catmaid.get_source()` is successfully run a ServerSource, a child of the [Source class](https://github.com/htem/catmaid_tools/blob/module/catmaid/source.py#L60), is returned based on a server defined by the environment variables above. This ServerSource has built in methods to fetch and/or save skeletons and neurons from the server.

## Examples

Please see [docs/notebooks](docs/notebooks) for an ipython notebook on how to get started.
