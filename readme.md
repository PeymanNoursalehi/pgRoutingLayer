# Welcome to PgRouting Layer!

A plugin for QGIS by Anita Graser and Ko Nagase

* project home and bug tracker: https://github.com/anitagraser/pgRoutingLayer
* plugin repository: none yet
* Wiki: https://github.com/anitagraser/pgRoutingLayer/wiki


## What is the goal

PgRouting Layer is a plugin for QGIS that serves as a GUI for pgRouting - a popular routing solution for PostGIS databases.

## What this plugin currently does

PgRoutingLayer supports the following functions:

* alphashape
* astar
* bdAstar
* bdDijkstra
* dijkstra
* drivingDistance
* kdijkstra_cost
* kdijkstra_path
* ksp
* shootingStar
* trsp_edge
* trsp_vertex
* tsp_euclid

## License

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

## Installation

To install this plugin, download the zipped repository from https://github.com/anitagraser/pgRoutingLayer/zipball/master

Unpack the zip file into your ~/.qgis2/python/plugins folder.

After a restart of QGIS, you should see the plugin available and activated in Plugin Manager.

### Dependencies

You'll need pgRouting up and running to use this plugin.

Additionally, QGIS needs python-psycopg2 installed to be able to connect to the database.
