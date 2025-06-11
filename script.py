import os
import pathlib
import json
import shutil
import random
import sys
random.seed(42)
rootdir = os.path.dirname(__file__)
l = os.listdir(rootdir)
dirlist = []
tspth = os.path.join(rootdir, 'test')
trpth = os.path.join(rootdir, 'train')
vldpth = os.path.join(rootdir, 'valid')
try:
    shutil.rmtree(trpth)
except Exception as e:
    print(e)
try:
    shutil.rmtree(tspth)
except Exception as e:
    print(e)
try:
    shutil.rmtree(vldpth)
except Exception as e:
    print(e)
for i in l:
    if(os.path.isdir(os.path.join(rootdir, i))):
        dirlist.append(os.path.join(rootdir, i))
try:
    os.mkdir(trpth)
except Exception as e:
    print(e)
try:
    os.mkdir(tspth)
except Exception as e:
    print(e)
try:
    os.mkdir(vldpth)
except Exception as e:
    print(e)
annodic = {}
imgdic = {}
tsglcount = 1
tsglcount2 = 0
trglcount = 1
trglcount2 = 0
vldglcount = 1
vldglcount2 = 0
tsout = {
    'info' : {
         "description": "my-project-name"
    },
    "categories": [
        {
            "id": 1,
            "name": "solarpv"
        }
    ],
    'images' : [

    ],
    'annotations':[

    ]
}
trout = {
    'info' : {
         "description": "my-project-name"
    },
    "categories": [
        {
            "id": 1,
            "name": "solarpv"
        }
    ],
    'images' : [

    ],
    'annotations':[

    ]
}
vldout = {
    'info' : {
         "description": "my-project-name"
    },
    "categories": [
        {
            "id": 1,
            "name": "solarpv"
        }
    ],
    'images' : [

    ],
    'annotations':[

    ]
}
for i in dirlist:
    for subdir, dirs, files in os.walk(i):
        for file in files:
            if file[-4:] == 'json':
                annodic[i] = os.path.join(i, file)
    f = open(annodic[i])
    data = json.load(f)
    f.close()
    imgdic[i] = {}
    count = 1
    added = []
    for j in data['images']:
        imgdic[i][j['id']] = os.path.join(i, j['file_name'])
        added.append(j['file_name'])
        count += 1
    for subdir, dirs, files in os.walk(i):
        for file in files:
            if file[-3:] == 'png':
                if file in added:
                    continue
                imgdic[i][count] = os.path.join(i, file)
                count += 1
    for i, j in imgdic[i].items():
        ch = random.choices(population=['tr', 'vld', 'ts'], weights= [0.8, 0.1,0.1])[0]
        if ch == 'ts':
            img = {
                "id": tsglcount,
                "width": 640,
                "height": 640,
                "file_name": str(tsglcount) + '.png'
            }
            shutil.copy(j, os.path.join(tspth, str(tsglcount) + '.png'))
            for k in data['annotations']:
                if k['image_id'] == i:
                    ann = k
                    ann['id'] = tsglcount2
                    tsglcount2 += 1
                    ann['image_id'] = tsglcount
                    tsout['annotations'].append(ann.copy())
            tsout['images'].append(img)
            tsglcount += 1
        elif ch == 'tr':
            img = {
                "id": trglcount,
                "width": 640,
                "height": 640,
                "file_name": str(trglcount) + '.png'
            }
            shutil.copy(j, os.path.join(trpth, str(trglcount) + '.png'))
            for k in data['annotations']:
                if k['image_id'] == i:
                    ann = k
                    ann['id'] = trglcount2
                    trglcount2 += 1
                    ann['image_id'] = trglcount
                    trout['annotations'].append(ann.copy())
            trout['images'].append(img)
            trglcount += 1
        elif ch == 'vld':
            img = {
                "id": vldglcount,
                "width": 640,
                "height": 640,
                "file_name": str(vldglcount) + '.png'
            }
            shutil.copy(j, os.path.join(vldpth, str(vldglcount) + '.png'))
            for k in data['annotations']:
                if k['image_id'] == i:
                    ann = k
                    ann['id'] = vldglcount2
                    vldglcount2 += 1
                    ann['image_id'] = vldglcount
                    vldout['annotations'].append(ann.copy())
            vldout['images'].append(img)
            vldglcount += 1
            
with open(os.path.join(trpth, '_annotations.coco.json'), 'w') as f:
    f.write(json.dumps(trout, indent = 6))
with open(os.path.join(tspth, '_annotations.coco.json'), 'w') as f:
    f.write(json.dumps(tsout, indent = 6))
with open(os.path.join(vldpth, '_annotations.coco.json'), 'w') as f:
    f.write(json.dumps(vldout, indent = 6))




        


    

    
    

