import numpy as np 
import pyproj
import OPSConfig

class OPSCreation:
    def __init__(self, icaoCode:str,THRs:dict,rwyCodeNum:int = None,rwyLength:int = None) -> None:
        # setting initial params
        self.icaoCode = icaoCode
        self.centerlineRWY:dict = {}
        self.rwyDirection = []
        if rwyLength != None:
            self.rwyLength = rwyLength
        if rwyCodeNum != None:
            self.rwyCodeNum = rwyCodeNum

        else:
            self.RwyCount = len(THRs)
            for i in range(0,self.RwyCount//2,2):
                self.rwyDirection.append(THRs[i]["designation"])
                self.rwyDirection.append(THRs[i+1]["designation"])
                self.centerlineRWY = self.createCenterlineRWY(icaoCode,THRs[i],THRs[i+1])
                self.rwyLength = self.centerlineRWY[f'{THRs[i]["designation"]}']["dist"]
                self.rwyCodeNum = self.getRWYCodeNumber(self.centerlineRWY[f'{THRs[i]["designation"]}']["dist"])
    
    def getDimAndSlope(self, rwyCodeNum:int, slopeIndicatorSys:str,rwyTypeCode:int=None,  eps:float=20.)->dict:
        # to get dimension and slope details, runway code number and slope indicator system should be input
        if rwyTypeCode == None:
            rwyTypeCode = self.getRwyType(rwyCodeNum)
        self.rwyCodeNum = rwyCodeNum
        planeDimSlope:dict = {
            "LenOfInnerEdge": self.getLengthOfInnerEdge(rwyTypeCode,rwyCodeNum, slopeIndicatorSys),
            "DistfromVisApproachSlopeIndiSystem":OPSConfig.OPSSlopeDims[rwyTypeCode]["DistfromVisApproachSlopeIndiSystem"][rwyCodeNum -1],
            "Divergence":OPSConfig.OPSSlopeDims[rwyTypeCode]["Divergence"][rwyCodeNum-1],
            "total_length":self.getTotalLength(rwyCodeNum, slopeIndicatorSys,rwyTypeCode),
            "slope": self. getSlopeIndicatorVal(slopeIndicatorSys, rwyTypeCode, rwyCodeNum,eps)
        }
        return planeDimSlope

    def getTotalLength(self, rwyCodeNum:int, slopeIndicatorSys:str, rwyTypeCode:int)->int:
        if slopeIndicatorSys in ["T-VASIS", "A-VASIS"] and rwyCodeNum == 2:
            return OPSConfig.OPSSlopeDims[rwyTypeCode]["total_length"][1][-1]
        else:
            return OPSConfig.OPSSlopeDims[rwyTypeCode]["total_length"][rwyCodeNum-1][0]
        
    def getLengthOfInnerEdge(self,rwyTypeCode:int, rwyCodeNumb:int, SlopeIndiSys:str)->int:
        if SlopeIndiSys in ["T-VASIS","A-VASIS"] and rwyCodeNumb == 2:
            return OPSConfig.OPSSlopeDims[rwyTypeCode]["LenOfInnerEdge"][rwyCodeNumb-1][-1]
        else:
            return OPSConfig.OPSSlopeDims[rwyTypeCode]["LenOfInnerEdge"][rwyCodeNumb-1][0]
        
    def getRwyType(self,rwyCodeNumber:int)->int:

        if rwyCodeNumber < 3:
            return 0
        else:
            return 1

        
    def createInitOPS(self, DimAndSlopeParams:dict, THR:dict, slopeIndicatorVal:float)->np.array:
        THRAZ = self.centerlineRWY[THR["designation"]]
        
        riseOfSurface = self.riseOfOPS(DimAndSlopeParams["total_length"],slopeIndicatorVal + DimAndSlopeParams["slope"])
        startOffset = self.calculateNewPosition(np.array(THR["coord"]),THRAZ["AZ_bwd"],DimAndSlopeParams["DistfromVisApproachSlopeIndiSystem"])
        endOffset = self.calculateNewPosition(np.array(THR["coord"]),THRAZ["AZ_bwd"], DimAndSlopeParams["DistfromVisApproachSlopeIndiSystem"] + DimAndSlopeParams["total_length"] )
        endOffset[-1] = endOffset[-1] + riseOfSurface
        return np.array([startOffset,endOffset])

    def creatSurfacePlane(self,DimAndSlopeParams:dict, slopeIndicatorVal:float,THR:dict,D1:float=None)->dict:
        """
        Input: 
            - rwyCodeNumber
            - slope indicator system (T-VASIS or A-VASIS, PAPI, APAPI)
            In addition, we need dimension configuration as follows:
                - length of inner edge
                - total length
                - slope of the plane 
        Return:
            {
            geometry:{
                coordinates:[set of coordinates]
            }
            }
        1. start with get all the configuration for creating the plane
        2. create the offset line which is initialized at the distance from THR points
        3. send the offset line and create the plane
        4. return the set of coordinates
        """
        THRAZ = self.centerlineRWY[THR["designation"]]
        slopeOPS = self.getAngleA(slopeVal=slopeIndicatorVal)
        initCenterOffSurface = self.createInitOPS(DimAndSlopeParams=DimAndSlopeParams, slopeIndicatorVal=slopeOPS,THR=THR)
        surface = self.createOPS(THRAZ["AZ_bwd"],initCenterOffSurface,DimAndSlopeParams["total_length"],self.surfaceDivergence(DimAndSlopeParams["total_length"],DimAndSlopeParams["Divergence"]),lengthOffInnerEdge=DimAndSlopeParams["LenOfInnerEdge"])
        self.initCenterlineOffSurface = initCenterOffSurface
        return {
            "type":"Feature",
            "properties":{
                "THR":THR["designation"],
                "SlopeIndSys":THR["slopeIndicatorSys"],
                "SlopeIndVal_deg":THR["slopeIndicatorVal"],
                "OPSslope_deg":slopeOPS,
                "total_length":DimAndSlopeParams["total_length"],
                "Divergence":DimAndSlopeParams["Divergence"],
                "LenOfInnderEdge":DimAndSlopeParams["LenOfInnerEdge"],
                "RwyType":OPSConfig.rwyTypeName[THR["rwyType"]],
                "RwyCodeNumber":self.rwyCodeNum
            },
            "geometry":{
                "type":"Polygon",
                "coordinates": [surface] 
            }
        }
    
    def getSlopeIndicatorVal(self, slopeIndicatorSys:str, rwyTypeCode:int, rwyCodeNum:int,eps:float=20.0)->float:
        VisAppSlopeIndi = OPSConfig.VisApproachSlopeIndi[slopeIndicatorSys]
        slopeVal = OPSConfig.OPSSlopeDims[rwyTypeCode]["slope"][VisAppSlopeIndi][rwyCodeNum-1]
        if slopeVal == None:
            slopeVal = 0.0

        return slopeVal 
                
    def getAngleA(self,slopeVal:float,eps:float=20)->float:
        # eps is the on-course sector which can be ranged from 20' to 30'
        eps = self.dms2dd(0,eps,0)
        
        angles = np.array([slopeVal + ((eps/2)+eps), slopeVal + (eps/2), slopeVal, slopeVal -(eps/2), slopeVal - ((eps/2)+eps)])

        return angles[-1]
    
    def getRWYCodeNumber(self,rwyDist:float)->int:
        if rwyDist < 800:
            return 1
        elif rwyDist >= 800 and rwyDist < 1200:
            return 2
        elif rwyDist >= 1200 and rwyDist < 1800:
            return 3
        else:
            return 4
    def dd2dms(self, dd:float)->dict:
        deg = int(dd)
        _min = (dd - deg)* 60
        sec = (_min - int(_min)) * 60
        
        dms:dict = {
            "deg": deg,
            "min": _min,
            "sec": sec
        }
        return dms

    def riseOfOPS(self, total_length:float, PAPI_slope_deg:float)->float:
        """
        input:
            - total length of the obstacle protection surface (meter)
            - PAPI slope (degree)
        return: rise (meter) of the surface 
            tan theta = rise / run 
        """
        PAPI_slope_rad = np.deg2rad(PAPI_slope_deg)
        rise_height = total_length * np.tan(PAPI_slope_rad)

        return rise_height

    def surfaceDivergence(self, total_length:float, diver:float)->float:
        """
        Input: 
            - total length of the obstacle protection surface (meter)
            - divergence on each side of the surface plane (percentage)
        Return:
            total_length * (divergen/100)
            returned unit will be meter
        """

        return total_length * (diver / 100.)

    def createCenterlineRWY(self, icaoCode:str,st_THR:dict, ed_THR:dict)->dict:
        # Noted: all the calculation base on WGS84
        # 1. receive the coordinate of THRs as the input
        # 2. Get forward and backward AZ angles and distance 
        # Output of this function will as follows:
        #   {ICAO code: 
        #       {
        #       "direction(ex. 18_36)":{
        #           AZ_fwd: ....
        #           AZ_bwd: ....
        #           dist: ....
        #           },
        #       "direction(ex. 36_18)":{ 
        #           AZ_fwd: ....
        #           AZ_bwd: ....
        #           dist: ....
        #           },   
        #       }
        # }
        g = pyproj.Geod(ellps=OPSConfig.projInUsed)
        fwd, bwd, dist = g.inv(st_THR["coord"][0],st_THR["coord"][1],ed_THR["coord"][0],ed_THR["coord"][1])
        centerLineInfo:dict = {

                f"{st_THR['designation']}":{
                    'AZ_fwd':fwd,
                    'AZ_bwd':bwd,
                    'dist':dist
                },
                f"{ed_THR['designation']}":{
                    'AZ_fwd':bwd,
                    'AZ_bwd':fwd,
                    'dist':dist
                }

        }

        return centerLineInfo

    def calculateNewPosition(self,orig_pos:np.ndarray,forwardAzimuth:float,dist:float)->list:
        g = pyproj.Geod(ellps=OPSConfig.projInUsed)
        endLon, endLat, backAzimuth = g.fwd(orig_pos[0], orig_pos[1], forwardAzimuth, dist)
        if orig_pos.size == 3:
            return [endLon, endLat, orig_pos[-1]]
        else:
            return [endLon,endLat,0.0]
    
    def dms2dd(self,deg:int, min:int, sec:float)->float:
        if deg < 360:
            deg = deg 
        else:
            deg = False
        if min < 60:
            min = min  
        else:
            min = False
        if sec < 60:
            sec = sec 
        else:
            sec = False
        if bool not in [type(deg), type(min), type(sec)]:
            DD = deg + (min/60) + (sec/3600)
            return DD
        else:
            raise Exception("Sorry, something is wrong with the inputs")
        
    def createOPS(self,truebrng:float,centerline_OPS:np.array,total_length:float, divergence_dist:float,lengthOffInnerEdge:float)->list:
        coords = []
        angles = np.array([-90.0, 90.0])
        dists = np.array([lengthOffInnerEdge, lengthOffInnerEdge + divergence_dist])
        for ang in angles:
            for pt, dist in zip(centerline_OPS,dists):
                # calculate new position
                newPt = self.calculateNewPosition(pt,truebrng + ang, dist)
                coords.append(newPt)
        coords.append(coords[0])
        moveIdx = [0,2,3,1,4]
        coords = [coords[i] for i in moveIdx]
        # output format
        surfaceOPS:list = coords

        return surfaceOPS