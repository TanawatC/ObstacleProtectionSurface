SurfaceExportDir = "export"  
projInUsed = 'WGS84'
rwyTypeCode = [
    0, # Non Instrument
    1  # Instrument
]
rwyTypeName = ["Non Instrument", "Instrument"]
VisApproachSlopeIndi = {"T-VASIS":"a","AT-VASIS":"a","PAPI":"b","APAPI":"c"}
OPSSlopeDims = {
    0:{
            "LenOfInnerEdge":[[60/2,60/2],[80/2,150/2],[150/2,150/2],[150/2,150/2]],
            "DistfromVisApproachSlopeIndiSystem":[30,60,60,60],
            "Divergence":[10,10,10,10],
            "total_length":[[7500],[7500,15000],[15000],[15000]],
            "slope":{
                "a":[None, 1.9,1.9,1.9],
                "b":[None,-0.57,-0.57,-0.57],
                "c":[-0.9,-0.9,None,None]
            }

    },
    1:{
            "LenOfInnerEdge":[[150/2],[150/2,300/2],[300/2],[300/2]],
            "DistfromVisApproachSlopeIndiSystem":[60,60,60,60],
            "Divergence":[15,15,15,15],
            "total_length":[[7500],[7500,15000],[15000],[15000]],
            "slope":{
                "a":[None, 1.9,1.9,1.9],
                "b":[-0.57,-0.57,-0.57,-0.57],
                "c":[-0.9,-0.9,None,None]
            }

    }
}

