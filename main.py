from OPSurface import OPSCreation
import OPSConfig
import json
import pyproj
from osgeo import ogr
import numpy as np
import pandas as pd

def _runCreateOPS(_input:dict,OPSonSpecificTHR:int)->dict:
    """
    Suppose we have the input of some airport, let say VTPO
    The input is provided runway type, runway code number (if), thresholds
    
    Noted that slope indicator system should be defined as the list here
        - T-VASIS, A-VASIS, PAPI, and APAPI

    OPSonSpecificTHR param allows to be only in the specific dense spares (
        0 = first THR,
        1 = end THR,
        2 = both THRs
        )
    
    """
    
    OPSsurface = OPSCreation(_input["icaoCode"],_input["THRs"])
    surfaceAsFeatures = []
    initCenterlineOffSurface = {}

    surfaceDimConfigs = None
    if _input["rwyCodeNum"] == None:
        print("rwyCodeNum not None")
        _input["rwyCodeNum"] = OPSsurface.getRWYCodeNumber(_input["rwyLength"])

    if OPSonSpecificTHR == 2:
        # loop
        print("Consider both rwys")
        
        for i in range(0,len(OPSsurface.rwyDirection)):
            surfaceDimConfigs = OPSsurface.getDimAndSlope(rwyCodeNum=_input["rwyCodeNum"],slopeIndicatorSys=_input["THRs"][i]["slopeIndicatorSys"],rwyTypeCode=_input["THRs"][i]["rwyType"])
            surface = OPSsurface.creatSurfacePlane(surfaceDimConfigs,_input["THRs"][i]["slopeIndicatorVal"],_input["THRs"][i])
            initCenterlineOffSurface[_input["THRs"][i]["designation"]] = OPSsurface.initCenterlineOffSurface
            surfaceAsFeatures.append(surface)
    else:
        print("Specific rwy direction")
        print(OPSsurface.rwyDirection[OPSonSpecificTHR])
        surfaceDimConfigs = OPSsurface.getDimAndSlope(rwyCodeNum=_input["rwyCodeNum"],slopeIndicatorSys=_input["THRs"][OPSonSpecificTHR]["slopeIndicatorSys"],rwyTypeCode=_input["THRs"][OPSonSpecificTHR]["rwyType"])
        surface = OPSsurface.creatSurfacePlane(DimAndSlopeParams=surfaceDimConfigs,slopeIndicatorVal=_input["THRs"][OPSonSpecificTHR]["slopeIndicatorVal"],THR=_input["THRs"][OPSonSpecificTHR])
        initCenterlineOffSurface[_input["THRs"][OPSonSpecificTHR]["designation"]] = OPSsurface.initCenterlineOffSurface
        surfaceAsFeatures.append(surface)
    return {
        "SurfaceFeature":{
            "type":"FeatureCollection",
            "features":surfaceAsFeatures
        },
        "initCenterlineOffSurface":initCenterlineOffSurface
    }

def _exportOPSsurface(AirportName:str,SurfaceAsGeoJSON:dict)->None:
    SurfaceExportDir = OPSConfig.SurfaceExportDir
    with open(f"{SurfaceExportDir}/{AirportName}_OPS.geojson",'w') as f:
        json.dump(SurfaceAsGeoJSON,f)



def _detect( initCenterlineOff:list, objects:list,OPSslopeVal_deg:float)->np.array:
    detectResult = {
        "allowance":False,
        "overtake":0.0
    }
    # check elevation

    distSp = _getSpDist(obj=objects,OPSOffsetCenterline=initCenterlineOff)
    riseHeight =_heightAllowance(OPSslopeVal_deg, distSp)
    print("dist: {}".format(distSp))
    print("Object Elevation: {} and Elevation of the surface: {}".format(objects[-1], (initCenterlineOff[0][-1] + riseHeight)))
    diffHeight = objects[-1] - (initCenterlineOff[0][-1] + riseHeight)
    # detectResult["allowance"] =  True if diffHeight<0.0 else False
    # detectResult["overtake"] = objects[-1] - (initCenterlineOff[0][-1] + riseHeight)
    # print("overtake", detectResult["overtake"])
    return [True if diffHeight<0.0 else False,
        objects[-1] - (initCenterlineOff[0][-1] + riseHeight)
    ]

def _runOPSDetection(surface:dict,objects:dict,OPSOffsetCenterline:dict)->dict:
    # Set OPS surface as Polygon geometry of gdal framework
    surfaceGeom = ogr.CreateGeometryFromJson(json.dumps(surface["geometry"]))
    OPSdetected = {
        "IDNumber":[],
        "Lat":[],
        "Lon":[],
        "Elevation":[],
        "Type":[],
        "geometry":[],
        "geom":[],
        "allowance":[],
        "overtake":[]
    }
    for _key in objects:
        objGeom = ogr.CreateGeometryFromWkt(objects[_key]["geom"])
        if objGeom.Intersect(surfaceGeom) == True:
            if objects[_key]["Geometry"].upper() == "POLYGON":
                print("IDNumber {}".format(objects[_key]["IDNumber"].upper()))
                cenX, cenY = objGeom.Centroid().GetX(), objGeom.Centroid().GetY()
                detectResulted = _detect(OPSOffsetCenterline,[cenX,cenY,objects[_key]["Elev"]],surface["properties"]["OPSslope_deg"])
                OPSdetected["IDNumber"].append(objects[_key]["IDNumber"])
                OPSdetected["Lon"].append(cenX)
                OPSdetected["Lat"].append(cenY)
                OPSdetected["Elevation"].append(objects[_key]["Elev"])
                OPSdetected["Type"].append(objects[_key]["Type"])
                OPSdetected["geometry"].append("Polygon")
                OPSdetected["geom"].append(objGeom)
                OPSdetected["allowance"].append(detectResulted[0])
                OPSdetected["overtake"].append(round(detectResulted[-1] ,3))

            
            elif objects[_key]["Geometry"].upper() == "LINE":
                print("IDNumber {}".format(objects[_key]["IDNumber"].upper()))
                cenX, cenY = objGeom.Centroid().GetX(), objGeom.Centroid().GetY()
                detectResulted = _detect(OPSOffsetCenterline,[cenX,cenY,objects[_key]["Elev"]],surface["properties"]["OPSslope_deg"])
                # print(detectResulted)
                OPSdetected["IDNumber"].append(objects[_key]["IDNumber"])
                OPSdetected["Lon"].append(cenX)
                OPSdetected["Lat"].append(cenY)
                OPSdetected["Elevation"].append(objects[_key]["Elev"])
                OPSdetected["Type"].append(objects[_key]["Type"])
                OPSdetected["geometry"].append("Line")
                OPSdetected["geom"].append(objGeom)
                OPSdetected["allowance"].append(detectResulted[0])
                OPSdetected["overtake"].append(round(detectResulted[-1] ,3))

            else:
                print("IDNumber {}".format(objects[_key]["IDNumber"].upper()))
                cenX, cenY = objects[_key]["Longitude"], objects[_key]["Latitude"]
                detectResulted = _detect(OPSOffsetCenterline,[cenX,cenY,objects[_key]["Elev"]],surface["properties"]["OPSslope_deg"])
                OPSdetected["IDNumber"].append(objects[_key]["IDNumber"])
                OPSdetected["Lon"].append(cenX)
                OPSdetected["Lat"].append(cenY)
                OPSdetected["Elevation"].append(objects[_key]["Elev"])
                OPSdetected["Type"].append(objects[_key]["Type"])
                OPSdetected["geometry"].append("Point")
                OPSdetected["geom"].append(objGeom)
                OPSdetected["allowance"].append(detectResulted[0])
                OPSdetected["overtake"].append(round(detectResulted[-1] ,3))
        else:
            continue
    return OPSdetected

def _heightAllowance(OPSslopeVal_deg:float,dist:float)->float:
    """
    OPSslopeVal: a slope angle of the OPS which is specified in degree
    """
    OPSslopeVal_rad = np.deg2rad(OPSslopeVal_deg)
    rise_height = dist * np.tan(OPSslopeVal_rad)


    return rise_height

def _getSpDist(obj:list,OPSOffsetCenterline:list)->float:
    g = pyproj.Geod(ellps=OPSConfig.projInUsed)

    px = OPSOffsetCenterline[1][0] - OPSOffsetCenterline[0][0]
    py = OPSOffsetCenterline[1][1] - OPSOffsetCenterline[0][1]
    dAB = px*px + py*py
    u = ((obj[0] - OPSOffsetCenterline[0][0] ) * px + (obj[1] - OPSOffsetCenterline[0][1]) * py) / dAB
    newX = OPSOffsetCenterline[0][0]+ u * px
    newY = OPSOffsetCenterline[0][1]+ u * py
    fwd3,bwd3, distFromOrigOffToSpecificPoint = g.inv(OPSOffsetCenterline[0][0],OPSOffsetCenterline[0][1],newX,newY)
    # print(newX , newY)
    return distFromOrigOffToSpecificPoint

def data_aggre(datasets,attr_names)->dict:

    data_merged = {}
    for dataset in datasets:
        print(f"Number of features in the dataset: {len(dataset)}")
        for i in range(0,len(dataset)):
            f = dataset.GetFeature(i)
            g = f.geometry()
            data_merged[dataset[i].GetField('IDNumber')] = {}

            data_merged[dataset[i].GetField('IDNumber')]["geom"] = g.ExportToWkt()

            for attr_name in attr_names:
                print(f"{dataset[i].GetField('IDNumber')}---->{attr_name}")
                data_merged[dataset[i].GetField('IDNumber')][attr_name] = dataset[i].GetField(attr_name)

    print(f"Total number of merged features : {len(data_merged)}")
    # print("---Sample of the attributes----")
    # print(data_merged[datasets[0][0].GetField('IDNumber')])

    return data_merged

def load_obstacleDataset(_dir)->dict:
    # Area2
    # VTPO lidar
    lidar_point2 = ogr.Open(_dir+'Area2_Obstacle/'+'Point_Obstacles.shp')
    lidar_line2 = ogr.Open(_dir+'Area2_Obstacle/'+'Line_Obstacles.shp')
    lidar_polygon2 = ogr.Open(_dir+'Area2_Obstacle/'+'Polygon_Obstacles.shp')


    lidar_point_ds_2 = lidar_point2.GetLayer()
    lidar_line_ds_2 = lidar_line2.GetLayer()
    lidar_polygon_ds_2 = lidar_polygon2.GetLayer()


    lidar_point_ds_2 = lidar_point_ds_2.GetLayer()
    ldfn = lidar_point_ds_2.GetLayerDefn()
    attr_names = [ldfn.GetFieldDefn(n).name for n in range(ldfn.GetFieldCount())]

    dataset_merged = data_aggre([ lidar_point_ds_2, lidar_line_ds_2, lidar_polygon_ds_2],attr_names)
    return dataset_merged

def _exportResultAsTable(detectedResult,fname:str)->None:
    colName =["IDNumber",
        "Lat",
        "Lon",
        "Elevation",
        "Type",
        "geometry",
        "overtake"]
    

    df  = pd.DataFrame(detectedResult, columns= colName)
    print(df.head())
    df.to_csv(fname)

def test():

    # THR coordinate from survey
    rwyDirection = 1
    _sampleinput:dict = {
        "icaoCode":"VTPO",
        "rwyCodeNum":4,
        "rwyLength":2100,
        "THRs":[{
            "designation":"18",
            "slopeIndicatorSys":'PAPI',
            "slopeIndicatorVal": 3., # unit in degree
            "coord":[99.818517,
17.247186,
54.5],
            "rwyType":1,
            "D1":None # is not in the use
            },
            {
            "designation":"36",
            "slopeIndicatorSys": "PAPI",
            "slopeIndicatorVal": 3.,
            "coord" :[99.818131, 17.228211,54.5],
            "rwyType":1,
            "D1":None
            }
        ]
    }

    sampleObject= load_obstacleDataset('D:/Python/Delv/66/OPS/doc/dataset/VTPO/')

    OPSAsGeoJSON = _runCreateOPS(_input = _sampleinput, OPSonSpecificTHR=rwyDirection)
    print(OPSAsGeoJSON)
    detectResulted = _runOPSDetection(surface=OPSAsGeoJSON["SurfaceFeature"]["features"][0],objects=sampleObject,OPSOffsetCenterline=OPSAsGeoJSON["initCenterlineOffSurface"][_sampleinput["THRs"][rwyDirection]["designation"]])

    # print(detectResulted)
    # # export ...
    _exportOPSsurface(_sampleinput["icaoCode"],OPSAsGeoJSON["SurfaceFeature"])
    _exportResultAsTable(detectResulted, "export/VTPO_OPS_Obstacle_Detected_THR36_rev1.csv")

test()
    