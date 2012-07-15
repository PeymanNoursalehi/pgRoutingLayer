﻿"""
/***************************************************************************
 pgRouting Layer
                                 a QGIS plugin
                                 
 based on "Fast SQL Layer" plugin. Copyright 2011 Pablo Torres Carreira 
                             -------------------
        begin                : 2011-11-25
        copyright            : (c) 2011 by Anita Graser
        email                : anita.graser.at@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
# Import the PyQt and QGIS libraries
from PyQt4 import uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
import dbConnection
#import highlighter as hl
import os
import psycopg2
import re

conn = dbConnection.ConnectionManager()

class PgRoutingLayer:
    # find nearest node/link radius(pix)
    FIND_RADIUS = 10
    idsEmitPoint = None
    sourceIdEmitPoint = None
    targetIdEmitPoint = None
    idsVertexMarkers = None
    sourceIdVertexMarker = None
    targetIdVertexMarker = None
    sourceIdRubberBand = None
    targetIdRubberBand = None
    resultNodesVertexMarkers = None
    resultNodesTextAnnotations = None
    resultPathRubberBand = None
    resultAreaRubberBand = None
    toggleControlNames = [
        'lineEditId', 'lineEditSource', 'lineEditTarget',
        'lineEditCost', 'lineEditReverseCost',
        'lineEditX1', 'lineEditY1', 'lineEditX2', 'lineEditY2',
        'lineEditRule', 'lineEditToCost',
        'lineEditIds', 'buttonSelectIds',
        'lineEditSourceId', 'buttonSelectSourceId',
        'lineEditTargetId', 'buttonSelectTargetId',
        'lineEditDistance',
        'checkBoxDirected', 'checkBoxHasReverseCost',
        'buttonExport'
    ]
    functionControlNamesList = {
        'shortest_path' : [
            'lineEditId', 'lineEditSource', 'lineEditTarget',
            'lineEditCost', 'lineEditReverseCost',
            'lineEditSourceId', 'buttonSelectSourceId',
            'lineEditTargetId', 'buttonSelectTargetId',
            'checkBoxDirected', 'checkBoxHasReverseCost',
            'buttonExport'
        ],
        'shortest_path_astar' : [
            'lineEditId', 'lineEditSource', 'lineEditTarget',
            'lineEditCost', 'lineEditReverseCost',
            'lineEditX1', 'lineEditY1', 'lineEditX2', 'lineEditY2',
            'lineEditSourceId', 'buttonSelectSourceId',
            'lineEditTargetId', 'buttonSelectTargetId',
            'checkBoxDirected', 'checkBoxHasReverseCost',
            'buttonExport'
        ],
        'shortest_path_shooting_star' : [
            'lineEditId', 'lineEditSource', 'lineEditTarget',
            'lineEditCost', 'lineEditReverseCost',
            'lineEditX1', 'lineEditY1', 'lineEditX2', 'lineEditY2',
            'lineEditRule', 'lineEditToCost',
            'lineEditSourceId', 'buttonSelectSourceId',
            'lineEditTargetId', 'buttonSelectTargetId',
            'checkBoxDirected', 'checkBoxHasReverseCost',
            'buttonExport'
        ],
        'driving_distance' : [
            'lineEditId', 'lineEditSource', 'lineEditTarget',
            'lineEditCost', 'lineEditReverseCost',
            'lineEditSourceId', 'buttonSelectSourceId',
            'lineEditDistance',
            'checkBoxDirected', 'checkBoxHasReverseCost'
        ],
        'alphashape' : [
            'lineEditId', 'lineEditSource', 'lineEditTarget',
            'lineEditCost', 'lineEditReverseCost',
            'lineEditSourceId', 'buttonSelectSourceId',
            'lineEditDistance',
            'checkBoxDirected', 'checkBoxHasReverseCost'
        ],
        # 'id' and 'target' are used for finding nearest node
        'tsp' : [
            'lineEditId', 'lineEditSource', 'lineEditTarget',
            'lineEditX1', 'lineEditY1',
            'lineEditIds', 'buttonSelectIds',
            'lineEditSourceId', 'buttonSelectSourceId'
        ]
    }
    nodeTableCreateQueryFormat = """
        CREATE TEMPORARY TABLE node AS
            SELECT id,
                ST_X(%(geometry)s) AS x,
                ST_Y(%(geometry)s) AS y,
                %(geometry)s
                FROM (
                    SELECT %(source)s AS id,
                        %(startpoint)s AS %(geometry)s
                        FROM %(edge_table)s
                    UNION
                    SELECT %(target)s AS id,
                        %(endpoint)s AS %(geometry)s
                        FROM %(edge_table)s
                ) AS node;"""
    functionQueryFormatList = {
        'shortest_path' : """
            SELECT * FROM shortest_path('
                SELECT %(id)s AS id,
                    %(source)s::int4 AS source,
                    %(target)s::int4 AS target,
                    %(cost)s::float8 AS cost%(reverse_cost)s
                    FROM %(edge_table)s',
                %(source_id)s, %(target_id)s, %(directed)s, %(has_reverse_cost)s)""",
        'shortest_path_astar' : """
            SELECT * FROM shortest_path_astar('
                SELECT %(id)s AS id,
                    %(source)s::int4 AS source,
                    %(target)s::int4 AS target,
                    %(cost)s::float8 AS cost%(reverse_cost)s,
                    %(x1)s::float8 AS x1,
                    %(y1)s::float8 AS y1,
                    %(x2)s::float8 AS x2,
                    %(y2)s::float8 AS y2
                    FROM %(edge_table)s',
                %(source_id)s, %(target_id)s, %(directed)s, %(has_reverse_cost)s)""",
        'shortest_path_shooting_star' : """
            SELECT * FROM shortest_path_shooting_star('
                SELECT %(id)s AS id,
                    %(source)s::int4 AS source,
                    %(target)s::int4 AS target,
                    %(cost)s::float8 AS cost%(reverse_cost)s,
                    %(x1)s::float8 AS x1,
                    %(y1)s::float8 AS y1,
                    %(x2)s::float8 AS x2,
                    %(y2)s::float8 AS y2,
                    %(rule)s::text AS rule,
                    %(to_cost)s::float8
                    FROM %(edge_table)s',
                %(source_id)s, %(target_id)s, %(directed)s, %(has_reverse_cost)s)""",
        'driving_distance' : """
            SELECT * FROM driving_distance('
                SELECT %(id)s AS id,
                    %(source)s::int4 AS source,
                    %(target)s::int4 AS target,
                    %(cost)s::float8 AS cost%(reverse_cost)s
                    FROM %(edge_table)s',
                %(source_id)s, %(distance)s, %(directed)s, %(has_reverse_cost)s)""",
        'alphashape' : """
            SELECT * FROM alphashape('
                SELECT *
                    FROM node
                    JOIN
                    (SELECT * FROM driving_distance(''
                        SELECT %(id)s AS id,
                            %(source)s::int4 AS source,
                            %(target)s::int4 AS target,
                            %(cost)s::float8 AS cost%(reverse_cost)s
                            FROM %(edge_table)s'',
                        %(source_id)s, %(distance)s, %(directed)s, %(has_reverse_cost)s))
                    AS dd ON node.id = dd.vertex_id'::text)""",
        'tsp' : """
            SELECT * FROM tsp('
                SELECT DISTINCT %(source)s AS source_id,
                    %(x1)s::float8 AS x,
                    %(y1)s::float8 AS y
                    FROM %(edge_table)s
                    WHERE %(source)s IN (%(ids)s)',
                '%(ids)s', %(source_id)s)"""
    }
    
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        
    def initGui(self):
        # Create action that will start plugin configuration
        self.action = QAction(QIcon(":/plugins/pgRoutingLayer/icon.png"), "pgRouting Layer", self.iface.mainWindow())
        #Add toolbar button and menu item
        self.iface.addPluginToDatabaseMenu("&pgRouting Layer", self.action)
        #self.iface.addToolBarIcon(self.action)
        
        #load the form
        path = os.path.dirname(os.path.abspath(__file__))
        self.dock = uic.loadUi(os.path.join(path, "ui_pgRoutingLayer.ui"))
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock)
        
        self.idsEmitPoint = QgsMapToolEmitPoint(self.iface.mapCanvas())
        #self.idsEmitPoint.setButton(buttonSelectIds)
        self.sourceIdEmitPoint = QgsMapToolEmitPoint(self.iface.mapCanvas())
        #self.sourceIdEmitPoint.setButton(buttonSelectSourceId)
        self.targetIdEmitPoint = QgsMapToolEmitPoint(self.iface.mapCanvas())
        #self.targetIdEmitPoint.setButton(buttonSelectTargetId)
        
        #connect the action to each method
        QObject.connect(self.action, SIGNAL("triggered()"), self.show)
        QObject.connect(self.dock.comboBoxFunction, SIGNAL("currentIndexChanged(const QString&)"), self.updateFunctionEnabled)
        QObject.connect(self.dock.buttonSelectIds, SIGNAL("clicked(bool)"), self.selectIds)
        QObject.connect(self.idsEmitPoint, SIGNAL("canvasClicked(const QgsPoint&, Qt::MouseButton)"), self.setIds)
        QObject.connect(self.dock.buttonSelectSourceId, SIGNAL("clicked(bool)"), self.selectSourceId)
        QObject.connect(self.sourceIdEmitPoint, SIGNAL("canvasClicked(const QgsPoint&, Qt::MouseButton)"), self.setSourceId)
        QObject.connect(self.dock.buttonSelectTargetId, SIGNAL("clicked(bool)"), self.selectTargetId)
        QObject.connect(self.targetIdEmitPoint, SIGNAL("canvasClicked(const QgsPoint&, Qt::MouseButton)"), self.setTargetId)
        QObject.connect(self.dock.checkBoxHasReverseCost, SIGNAL("stateChanged(int)"), self.updateReverseCostEnabled)
        QObject.connect(self.dock.buttonRun, SIGNAL("clicked()"), self.run)
        QObject.connect(self.dock.buttonExport, SIGNAL("clicked()"), self.export)
        QObject.connect(self.dock.buttonClear, SIGNAL("clicked()"), self.clear)
        
        #populate the combo with connections
        actions = conn.getAvailableConnections()
        self.actionsDb = {}
        for a in actions:
            self.actionsDb[ unicode(a.text()) ] = a
        for i in self.actionsDb:
            self.dock.comboConnections.addItem(i)
        
        #self.dock.lineEditTable.setText('at_2po_4pgr')
        #self.dock.lineEditGeometry.setText('geom_way')
        self.dock.lineEditTable.setText('roads')
        self.dock.lineEditGeometry.setText('the_geom')
        
        self.dock.lineEditId.setText('id')
        self.dock.lineEditSource.setText('source')
        self.dock.lineEditTarget.setText('target')
        self.dock.lineEditCost.setText('cost')
        self.dock.lineEditReverseCost.setText('reverse_cost')
        self.dock.lineEditX1.setText('x1')
        self.dock.lineEditY1.setText('y1')
        self.dock.lineEditX2.setText('x2')
        self.dock.lineEditY2.setText('y2')
        self.dock.lineEditRule.setText('rule')
        self.dock.lineEditToCost.setText('to_cost')
        
        #self.dock.lineEditSourceId.setText('191266')
        #self.dock.lineEditTargetId.setText('190866')
        
        self.dock.lineEditIds.setValidator(QRegExpValidator(QRegExp("[0-9,]+"), self.dock))
        self.dock.lineEditSourceId.setValidator(QIntValidator())
        self.dock.lineEditTargetId.setValidator(QIntValidator())
        
        self.idsVertexMarkers = []
        self.sourceIdVertexMarker = QgsVertexMarker(self.iface.mapCanvas())
        self.sourceIdVertexMarker.setColor(Qt.blue)
        self.sourceIdVertexMarker.setPenWidth(2)
        self.sourceIdVertexMarker.setVisible(False)
        self.targetIdVertexMarker = QgsVertexMarker(self.iface.mapCanvas())
        self.targetIdVertexMarker.setColor(Qt.green)
        self.targetIdVertexMarker.setPenWidth(2)
        self.targetIdVertexMarker.setVisible(False)
        self.sourceIdRubberBand = QgsRubberBand(self.iface.mapCanvas(), False)
        self.sourceIdRubberBand.setColor(Qt.cyan)
        self.sourceIdRubberBand.setWidth(4)
        self.targetIdRubberBand = QgsRubberBand(self.iface.mapCanvas(), False)
        self.targetIdRubberBand.setColor(Qt.yellow)
        self.targetIdRubberBand.setWidth(4)
        self.resultNodesVertexMarkers = []
        self.resultNodesTextAnnotations = []
        self.resultPathRubberBand = QgsRubberBand(self.iface.mapCanvas(), False)
        self.resultPathRubberBand.setColor(Qt.red)
        self.resultPathRubberBand.setWidth(2)
        self.resultAreaRubberBand = QgsRubberBand(self.iface.mapCanvas(), True)
        self.resultAreaRubberBand.setColor(Qt.magenta)
        self.resultAreaRubberBand.setWidth(2)
        
        self.dock.comboBoxFunction.setCurrentIndex(0)
        
    def show(self):
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock)
        
    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removePluginDatabaseMenu("&pgRouting Layer", self.action)
        self.iface.removeDockWidget(self.dock)
        
    def updateFunctionEnabled(self, text):
        self.toggleSelectButton(None)
        
        for controlName in self.toggleControlNames:
            control = getattr(self.dock, controlName)
            control.setEnabled(False)
        
        for controlName in self.functionControlNamesList[str(text)]:
            control = getattr(self.dock, controlName)
            control.setEnabled(True)
        
        if (not self.dock.checkBoxHasReverseCost.isChecked()) or (not self.dock.checkBoxHasReverseCost.isEnabled()):
            self.dock.lineEditReverseCost.setEnabled(False)
        
        # currently edge base function is "shortest_path_shooting_star" only
        if text == 'shortest_path_shooting_star':
            self.clear()
            
    def selectIds(self, checked):
        if checked:
            self.toggleSelectButton(self.dock.buttonSelectIds)
            self.dock.lineEditIds.setText("")
            if len(self.idsVertexMarkers) > 0:
                for marker in self.idsVertexMarkers:
                    marker.setVisible(False)
                self.idsVertexMarkers = []
            self.iface.mapCanvas().setMapTool(self.idsEmitPoint)
        else:
            self.iface.mapCanvas().unsetMapTool(self.idsEmitPoint)
        
    def setIds(self, pt):
        args = self.getBaseArguments()
        result, id, wkt = self.findNearestNode(args, pt)
        if result:
            ids = self.dock.lineEditIds.text()
            if not ids:
                self.dock.lineEditIds.setText(str(id))
            else:
                self.dock.lineEditIds.setText(ids + "," + str(id))
            geom = QgsGeometry().fromWkt(wkt)
            vertexMarker = QgsVertexMarker(self.iface.mapCanvas())
            vertexMarker.setColor(Qt.green)
            vertexMarker.setPenWidth(2)
            vertexMarker.setCenter(geom.asPoint())
            self.idsVertexMarkers.append(vertexMarker)
        
    def selectSourceId(self, checked):
        if checked:
            self.toggleSelectButton(self.dock.buttonSelectSourceId)
            self.dock.lineEditSourceId.setText("")
            self.sourceIdVertexMarker.setVisible(False)
            self.sourceIdRubberBand.reset(False)
            self.iface.mapCanvas().setMapTool(self.sourceIdEmitPoint)
        else:
            self.iface.mapCanvas().unsetMapTool(self.sourceIdEmitPoint)
        
    def setSourceId(self, pt):
        func = str(self.dock.comboBoxFunction.currentText())
        args = self.getBaseArguments()
        if func != 'shortest_path_shooting_star':
            result, id, wkt = self.findNearestNode(args, pt)
            if result:
                self.dock.lineEditSourceId.setText(str(id))
                geom = QgsGeometry().fromWkt(wkt)
                self.sourceIdVertexMarker.setCenter(geom.asPoint())
                self.sourceIdVertexMarker.setVisible(True)
                self.dock.buttonSelectSourceId.click()
        else:
            result, id, wkt = self.findNearestLink(args, pt)
            if result:
                self.dock.lineEditSourceId.setText(str(id))
                geom = QgsGeometry().fromWkt(wkt)
                if geom.wkbType() == QGis.WKBMultiLineString:
                    for line in geom.asMultiPolyline():
                        for pt in line:
                            self.sourceIdRubberBand.addPoint(pt)
                elif geom.wkbType() == QGis.WKBLineString:
                    for pt in geom.asPolyline():
                        self.sourceIdRubberBand.addPoint(pt)
                self.dock.buttonSelectSourceId.click()
        self.iface.mapCanvas().clear() # TODO:
        
    def selectTargetId(self, checked):
        if checked:
            self.toggleSelectButton(self.dock.buttonSelectTargetId)
            self.dock.lineEditTargetId.setText("")
            self.targetIdVertexMarker.setVisible(False)
            self.targetIdRubberBand.reset(False)
            self.iface.mapCanvas().setMapTool(self.targetIdEmitPoint)
        else:
            self.iface.mapCanvas().unsetMapTool(self.targetIdEmitPoint)
        
    def setTargetId(self, pt):
        func = str(self.dock.comboBoxFunction.currentText())
        args = self.getBaseArguments()
        if func != 'shortest_path_shooting_star':
            result, id, wkt = self.findNearestNode(args, pt)
            if result:
                self.dock.lineEditTargetId.setText(str(id))
                geom = QgsGeometry().fromWkt(wkt)
                self.targetIdVertexMarker.setCenter(geom.asPoint())
                self.targetIdVertexMarker.setVisible(True)
                self.dock.buttonSelectTargetId.click()
        else:
            result, id, wkt = self.findNearestLink(args, pt)
            if result:
                self.dock.lineEditTargetId.setText(str(id))
                geom = QgsGeometry().fromWkt(wkt)
                if geom.wkbType() == QGis.WKBMultiLineString:
                    for line in geom.asMultiPolyline():
                        for pt in line:
                            self.targetIdRubberBand.addPoint(pt)
                elif geom.wkbType() == QGis.WKBLineString:
                    for pt in geom.asPolyline():
                        self.targetIdRubberBand.addPoint(pt)
                self.dock.buttonSelectTargetId.click()
        self.iface.mapCanvas().clear() # TODO:
        
    def updateReverseCostEnabled(self, state):
        if state == Qt.Checked:
            self.dock.lineEditReverseCost.setEnabled(True)
        else:
            self.dock.lineEditReverseCost.setEnabled(False)
        
    def run(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        
        func = str(self.dock.comboBoxFunction.currentText())
        args = self.getArguments(self.functionControlNamesList[func])
        
        if func == 'driving_distance':
            for marker in self.resultNodesVertexMarkers:
                marker.setVisible(False)
            self.resultNodesVertexMarkers = []
        elif func == 'tsp':
            for anno in self.resultNodesTextAnnotations:
                anno.setVisible(False)
            self.resultNodesTextAnnotations = []
        self.resultPathRubberBand.reset(False)
        self.resultAreaRubberBand.reset(True)
        
        empties = []
        for key in args.keys():
            if not args[key]:
                empties.append(key)
        
        if len(empties) > 0:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self.dock, self.dock.windowTitle(),
                'Following argument is not specified.\n' + ','.join(empties))
            return
        
        query = self.functionQueryFormatList[func] % args
        ##QMessageBox.information(self.dock, self.dock.windowTitle(), query)
        
        try:
            dados = str(self.dock.comboConnections.currentText())
            db = self.actionsDb[dados].connect()
            
            con = db.con
            
            if (func == 'driving_distance') or (func == 'alphashape') or (func == 'tsp'):
                srid, geomType = self.getSridAndGeomType(con, args)
                if geomType == 'ST_MultiLineString':
                    args['startpoint'] = "ST_StartPoint(ST_GeometryN(%(geometry)s, 1))" % args
                    args['endpoint'] = "ST_EndPoint(ST_GeometryN(%(geometry)s, 1))" % args
                elif geomType == 'ST_LineString':
                    args['startpoint'] = "ST_StartPoint(%(geometry)s)" % args
                    args['endpoint'] = "ST_EndPoint(%(geometry)s)" % args
                
                if func == 'alphashape':
                    cur = con.cursor()
                    cur.execute(self.nodeTableCreateQueryFormat % args)
                    
            cur = con.cursor()
            cur.execute(query)
            rows = cur.fetchall()
            if func.startswith('shortest_path') or (func == 'driving_distance') or (func == 'tsp'):
                # return columns are 'vertex_id', 'edge_id', 'cost'
                i = 0
                for row in rows:
                    cur2 = con.cursor()
                    args['result_vertex_id'] = row[0]
                    args['result_edge_id'] = row[1]
                    args['result_cost'] = row[2]
                    if func.startswith('shortest_path'):
                        if args['result_edge_id'] != -1 or (func == 'shortest_path_shooting_star'):
                            query2 = """
                                SELECT ST_AsText(%(geometry)s) FROM %(edge_table)s
                                    WHERE %(source)s = %(result_vertex_id)d AND %(id)s = %(result_edge_id)d
                                UNION
                                SELECT ST_AsText(ST_Reverse(%(geometry)s)) FROM %(edge_table)s
                                    WHERE %(target)s = %(result_vertex_id)d AND %(id)s = %(result_edge_id)d;
                            """ % args
                            ##QMessageBox.information(self.dock, self.dock.windowTitle(), query2)
                            cur2.execute(query2)
                            row2 = cur2.fetchone()
                            ##QMessageBox.information(self.dock, self.dock.windowTitle(), str(row2[0]))
                            if not row2:
                                # TODO: shooting_star always returns invalid vertex_id!
                                QApplication.restoreOverrideCursor()
                                QMessageBox.critical(self.dock, self.dock.windowTitle(),
                                    "Invalid result geometry. (vertex_id:%(result_vertex_id)d, edge_id:%(result_edge_id)d)" % args)
                                return
                            geom = QgsGeometry().fromWkt(str(row2[0]))
                            if geom.wkbType() == QGis.WKBMultiLineString:
                                for line in geom.asMultiPolyline():
                                    for pt in line:
                                        self.resultPathRubberBand.addPoint(pt)
                            elif geom.wkbType() == QGis.WKBLineString:
                                for pt in geom.asPolyline():
                                    self.resultPathRubberBand.addPoint(pt)
                    elif (func == 'driving_distance'):
                        query2 = """
                            SELECT ST_AsText(%(startpoint)s) FROM %(edge_table)s
                                WHERE %(source)s = %(result_vertex_id)d AND %(id)s = %(result_edge_id)d
                            UNION
                            SELECT ST_AsText(%(endpoint)s) FROM %(edge_table)s
                                WHERE %(target)s = %(result_vertex_id)d AND %(id)s = %(result_edge_id)d
                        """ % args
                        cur2.execute(query2)
                        row2 = cur2.fetchone()
                        if not row2:
                            QApplication.restoreOverrideCursor()
                            QMessageBox.critical(self.dock, self.dock.windowTitle(),
                                "Invalid result geometry. (vertex_id:%(result_vertex_id)d, edge_id:%(result_edge_id)d)" % args)
                            return
                        geom = QgsGeometry().fromWkt(str(row2[0]))
                        pt = geom.asPoint()
                        vertexMarker = QgsVertexMarker(self.iface.mapCanvas())
                        vertexMarker.setColor(Qt.red)
                        vertexMarker.setPenWidth(2)
                        vertexMarker.setIconSize(5)
                        vertexMarker.setCenter(QgsPoint(pt))
                        self.resultNodesVertexMarkers.append(vertexMarker)
                    elif (func == 'tsp'):
                        query2 = """
                            SELECT ST_AsText(%(startpoint)s) FROM %(edge_table)s
                                WHERE %(source)s = %(result_vertex_id)d
                            UNION
                            SELECT ST_AsText(%(endpoint)s) FROM %(edge_table)s
                                WHERE %(target)s = %(result_vertex_id)d
                        """ % args
                        cur2.execute(query2)
                        row2 = cur2.fetchone()
                        if not row2:
                            QApplication.restoreOverrideCursor()
                            QMessageBox.critical(self.dock, self.dock.windowTitle(),
                                "Invalid result geometry. (vertex_id:%(result_vertex_id)d" % args)
                            return
                        geom = QgsGeometry().fromWkt(str(row2[0]))
                        pt = geom.asPoint()
                        i += 1
                        textAnnotation = QgsTextAnnotationItem(self.iface.mapCanvas())
                        textAnnotation.setMapPosition(geom.asPoint())
                        textAnnotation.setFrameSize(QSizeF(20,20))
                        textAnnotation.setOffsetFromReferencePoint(QPointF(20, -40))
                        textAnnotation.setDocument(QTextDocument(str(i)))
                        textAnnotation.update()
                        self.resultNodesTextAnnotations.append(textAnnotation)
            elif func == 'alphashape':
                # return columns are 'x', 'y'
                for row in rows:
                    x = row[0]
                    y = row[1]
                    self.resultAreaRubberBand.addPoint(QgsPoint(x, y))
            
        except psycopg2.DatabaseError, e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self.dock, self.dock.windowTitle(), '%s' % e)
            
        except SystemError, e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self.dock, self.dock.windowTitle(), '%s' % e)
            
        finally:
            QApplication.restoreOverrideCursor()
            if db and db.con:
                try:
                    db.con.close()
                except:
                    QMessageBox.critical(self.dock, self.dock.windowTitle(),
                        'server closed the connection unexpectedly')
        
    def export(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        
        func = str(self.dock.comboBoxFunction.currentText())
        args = self.getArguments(self.functionControlNamesList[func])
        
        empties = []
        for key in args.keys():
            if not args[key]:
                empties.append(key)
        
        if len(empties) > 0:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self.dock, self.dock.windowTitle(),
                'Following argument is not specified.\n' + ','.join(empties))
            return
        
        args['path_query'] = self.functionQueryFormatList[func] % args
        
        query = """
            SELECT %(edge_table)s.*,
                route.cost AS route_cost,
                route.vertex_id AS route_vertex_id
                FROM %(edge_table)s
                JOIN
                (%(path_query)s) AS route
                ON %(edge_table)s.%(id)s = route.edge_id""" % args
        
        query = query.replace('\n', ' ')
        query = re.sub(r'\s+', ' ', query)
        query = query.strip()
        ##QMessageBox.information(self.dock, self.dock.windowTitle(), query)
        
        try:
            dados = str(self.dock.comboConnections.currentText())
            db = self.actionsDb[dados].connect()
            
            uri = db.getURI()
            uri.setDataSource("", "(" + query + ")", args['geometry'], "", args['id'])
            
            # add vector layer to map
            layerName = "from "+args['source_id']+" to "+args['target_id']
            vl = self.iface.addVectorLayer(uri.uri(), layerName, db.getProviderName())
            
        except psycopg2.DatabaseError, e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self.dock, self.dock.windowTitle(), '%s' % e)
            
        except SystemError, e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self.dock, self.dock.windowTitle(), '%s' % e)
            
        finally:
            QApplication.restoreOverrideCursor()
            if db and db.con:
                try:
                    db.con.close()
                except:
                    QMessageBox.critical(self.dock, self.dock.windowTitle(),
                        'server closed the connection unexpectedly')
        
    def clear(self):
        self.dock.lineEditIds.setText("")
        for marker in self.idsVertexMarkers:
            marker.setVisible(False)
        self.idsVertexMarkers = []
        self.dock.lineEditSourceId.setText("")
        self.sourceIdVertexMarker.setVisible(False)
        self.dock.lineEditTargetId.setText("")
        self.targetIdVertexMarker.setVisible(False)
        self.sourceIdRubberBand.reset(False)
        self.targetIdRubberBand.reset(False)
        for marker in self.resultNodesVertexMarkers:
            marker.setVisible(False)
        self.resultNodesVertexMarkers = []
        for anno in self.resultNodesTextAnnotations:
            anno.setVisible(False)
        self.resultNodesTextAnnotations = []
        self.resultPathRubberBand.reset(False)
        self.resultAreaRubberBand.reset(True)
        
    def toggleSelectButton(self, button):
        selectButtons = [
            self.dock.buttonSelectIds,
            self.dock.buttonSelectSourceId,
            self.dock.buttonSelectTargetId
        ]
        for selectButton in selectButtons:
            if selectButton != button:
                if selectButton.isChecked():
                    selectButton.click()

    def getArguments(self, controls):
        args = {}
        args['edge_table'] = self.dock.lineEditTable.text()
        args['geometry'] = self.dock.lineEditGeometry.text()
        if 'lineEditId' in controls:
            args['id'] = self.dock.lineEditId.text()
        if 'lineEditSource' in controls:
            args['source'] = self.dock.lineEditSource.text()
        
        if 'lineEditTarget' in controls:
            args['target'] = self.dock.lineEditTarget.text()
        
        if 'lineEditCost' in controls:
            args['cost'] = self.dock.lineEditCost.text()
        
        if 'lineEditReverseCost' in controls:
            args['reverse_cost'] = self.dock.lineEditReverseCost.text()
        
        if 'lineEditX1' in controls:
            args['x1'] = self.dock.lineEditX1.text()
        
        if 'lineEditY1' in controls:
            args['y1'] = self.dock.lineEditY1.text()
        
        if 'lineEditX2' in controls:
            args['x2'] = self.dock.lineEditX2.text()
        
        if 'lineEditY2' in controls:
            args['y2'] = self.dock.lineEditY2.text()
        
        if 'lineEditRule' in controls:
            args['rule'] = self.dock.lineEditRule.text()
        
        if 'lineEditToCost' in controls:
            args['to_cost'] = self.dock.lineEditToCost.text()
        
        if 'lineEditSourceId' in controls:
            args['source_id'] = self.dock.lineEditSourceId.text()
        
        if 'lineEditTargetId' in controls:
            args['target_id'] = self.dock.lineEditTargetId.text()
        
        if 'lineEditIds' in controls:
            args['ids'] = self.dock.lineEditIds.text()
        
        if 'lineEditDistance' in controls:
            args['distance'] = self.dock.lineEditDistance.text()
        
        if 'checkBoxDirected' in controls:
            args['directed'] = str(self.dock.checkBoxDirected.isChecked()).lower()
        
        if 'checkBoxHasReverseCost' in controls:
            args['has_reverse_cost'] = str(self.dock.checkBoxHasReverseCost.isChecked()).lower()
            if args['has_reverse_cost'] == 'false':
                args['reverse_cost'] = ' '
            else:
                args['reverse_cost'] = ', ' + args['reverse_cost'] + '::float8 AS reverse_cost'
        
        return args
        
    def getBaseArguments(self):
        args = {}
        args['edge_table'] = self.dock.lineEditTable.text()
        args['geometry'] = self.dock.lineEditGeometry.text()
        args['id'] = self.dock.lineEditId.text()
        args['source'] = self.dock.lineEditSource.text()
        args['target'] = self.dock.lineEditTarget.text()
        
        empties = []
        for key in args.keys():
            if not args[key]:
                empties.append(key)
        
        if len(empties) > 0:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self.dock, self.dock.windowTitle(),
                'Following argument is not specified.\n' + ','.join(empties))
            return None
        
        return args
        
    def getSridAndGeomType(self, con, args):
        cur = con.cursor()
        cur.execute("""
            SELECT ST_SRID(%(geometry)s), ST_GeometryType(%(geometry)s)
                FROM %(edge_table)s
                WHERE %(id)s = (SELECT MIN(%(id)s) FROM %(edge_table)s)""" % args)
        row = cur.fetchone()
        srid = row[0]
        geomType = row[1]
        return srid, geomType
        
    # emulate "matching.sql" - "find_nearest_node_within_distance"
    def findNearestNode(self, args, pt):
        distance = self.iface.mapCanvas().getCoordinateTransform().mapUnitsPerPixel() * self.FIND_RADIUS
        try:
            dados = str(self.dock.comboConnections.currentText())
            db = self.actionsDb[dados].connect()
            
            con = db.con
            srid, geomType = self.getSridAndGeomType(con, args)
            args['srid'] = srid
            args['x'] = pt.x()
            args['y'] = pt.y()
            args['minx'] = pt.x() - distance
            args['miny'] = pt.y() - distance
            args['maxx'] = pt.x() + distance
            args['maxy'] = pt.y() + distance
            
            if geomType == 'ST_MultiLineString':
                args['startpoint'] = "ST_StartPoint(ST_GeometryN(%(geometry)s, 1))" % args
                args['endpoint'] = "ST_EndPoint(ST_GeometryN(%(geometry)s, 1))" % args
            elif geomType == 'ST_LineString':
                args['startpoint'] = "ST_StartPoint(%(geometry)s)" % args
                args['endpoint'] = "ST_EndPoint(%(geometry)s)" % args
            
            # Getting nearest source
            query1 = """
            SELECT %(source)s,
                ST_Distance(
                    %(startpoint)s,
                    ST_GeomFromText('POINT(%(x)f %(y)f)', %(srid)d)
                ) AS dist,
                ST_AsText(%(startpoint)s)
                FROM %(edge_table)s
                WHERE ST_SetSRID('BOX3D(%(minx)f %(miny)f, %(maxx)f %(maxy)f)'::BOX3D, %(srid)d)
                    && %(geometry)s ORDER BY dist ASC LIMIT 1""" % args
            
            ##QMessageBox.information(self.dock, self.dock.windowTitle(), query1)
            cur1 = con.cursor()
            cur1.execute(query1)
            row1 = cur1.fetchone()
            d1 = None
            source = None
            wkt1 = None
            if row1:
                d1 = row1[1]
                source = row1[0]
                wkt1 = row1[2]
            
            # Getting nearest target
            query2 = """
            SELECT %(target)s,
                ST_Distance(
                    %(endpoint)s,
                    ST_GeomFromText('POINT(%(x)f %(y)f)', %(srid)d)
                ) AS dist,
                ST_AsText(%(endpoint)s)
                FROM %(edge_table)s
                WHERE ST_SetSRID('BOX3D(%(minx)f %(miny)f, %(maxx)f %(maxy)f)'::BOX3D, %(srid)d)
                    && %(geometry)s ORDER BY dist ASC LIMIT 1""" % args
            
            ##QMessageBox.information(self.dock, self.dock.windowTitle(), query2)
            cur2 = con.cursor()
            cur2.execute(query2)
            row2 = cur2.fetchone()
            d2 = None
            target = None
            wkt2 = None
            if row2:
                d2 = row2[1]
                target = row2[0]
                wkt2 = row2[2]
            
            # Checking what is nearer - source or target
            d = None
            node = None
            wkt = None
            if d1 and (not d2):
                node = source
                d = d1
                wkt = wkt1
            elif (not d1) and d2:
                node = target
                d = d2
                wkt = wkt2
            elif d1 and d2:
                if d1 < d2:
                    node = source
                    d = d1
                    wkt = wkt1
                else:
                    node = target
                    d = d2
                    wkt = wkt2
            
            ##QMessageBox.information(self.dock, self.dock.windowTitle(), str(d))
            if (d == None) or (d > distance):
                node = None
                wkt = None
                return False, None, None
            
            return True, node, wkt
            
        except psycopg2.DatabaseError, e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self.dock, self.dock.windowTitle(), '%s' % e)
            return False, None, None
            
        finally:
            if db and db.con:
                db.con.close()
        
    # emulate "matching.sql" - "find_nearest_link_within_distance"
    def findNearestLink(self, args, pt):
        distance = self.iface.mapCanvas().getCoordinateTransform().mapUnitsPerPixel() * self.FIND_RADIUS
        try:
            dados = str(self.dock.comboConnections.currentText())
            db = self.actionsDb[dados].connect()
            
            con = db.con
            cur = con.cursor()
            cur.execute("""
                SELECT ST_SRID(%(geometry)s)
                    FROM %(edge_table)s
                    WHERE %(id)s = (SELECT MIN(%(id)s) FROM %(edge_table)s)""" % args)
            row = cur.fetchone()
            args['srid'] = row[0]
            args['x'] = pt.x()
            args['y'] = pt.y()
            args['minx'] = pt.x() - distance
            args['miny'] = pt.y() - distance
            args['maxx'] = pt.x() + distance
            args['maxy'] = pt.y() + distance
            
            # Searching for a link within the distance
            query = """
            SELECT %(id)s,
                ST_Distance(
                    %(geometry)s,
                    ST_GeomFromText('POINT(%(x)f %(y)f)', %(srid)d)
                ) AS dist,
                ST_AsText(%(geometry)s)
                FROM %(edge_table)s
                WHERE ST_SetSRID('BOX3D(%(minx)f %(miny)f, %(maxx)f %(maxy)f)'::BOX3D, %(srid)d)
                    && %(geometry)s ORDER BY dist ASC LIMIT 1""" % args
            
            ##QMessageBox.information(self.dock, self.dock.windowTitle(), query1)
            cur = con.cursor()
            cur.execute(query)
            row = cur.fetchone()
            if not row:
                return False, None, None
            link = row[0]
            wkt = row[2]
            
            return True, link, wkt
            
        except psycopg2.DatabaseError, e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self.dock, self.dock.windowTitle(), '%s' % e)
            return False, None, None
            
        finally:
            if db and db.con:
                db.con.close()
