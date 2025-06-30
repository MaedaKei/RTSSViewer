"""
病院から渡されたCT volumeとDICOM RTSSを重ねて、登録されている組織名とその囲いを視覚的に確認するViewer
学習データセットを作成する段階での使用を想定している
"""
import pydicom as dicom
import matplotlib.pyplot as plt
from matplotlib.path import Path
import matplotlib.patches as patches
import numpy as np
from colormap_forRTSS import colormap
import os,glob

class CTVolume:
    def __init__(self,CTVolume_dirpath,MASK_COLOR_LIMIT=30):
        #読み込む
        loadedslice_location = {}#読み込んだ順番と位置情報を辞書として保持する
        CT_image_list=[]#読み込んだ順にプールしていく
        filepath_list=glob.glob(os.path.join(CTVolume_dirpath,"*.dcm"))
        for i,filepath in enumerate(filepath_list):
            if dicom.misc.is_dicom(filepath):#DCMファイルかどうか
                DcmData=dicom.dcmread(filepath)
                if DcmData.SOPClassUID=="1.2.840.10008.5.1.4.1.1.2":#CTイメージかどうか
                    loadedslice_location[i]=float(DcmData.ImagePositionPatient[2])
                    img_data=DcmData.pixel_array*DcmData.RescaleSlope+DcmData.RescaleIntercept
                    CT_image_list.append(img_data)
        #位置情報を基に、画像を積み重ねる＆位置情報とindexの変換表を作っておく
        #CT画像のサイズは全て同じと仮定して動かす。同じじゃない場合エラーを吐き出させてとめるしかないため。
        position2index={}
        index2position={}
        ctvolume=[]
        for index,(loaded_index,position) in enumerate(sorted(loadedslice_location.items(),key=lambda x:-x[1])):
            position2index[position]=index
            index2position[index]=position
            ctvolume.append(CT_image_list[loaded_index])
        ctvolume=np.array(ctvolume)
        #ヒストグラム用の解析&セグメンテーションか判別
        pixel_unique,pixel_hist=np.unique(ctvolume,return_counts=True)
        pixel_hist[np.argmax(pixel_hist)]=0
        hist=[pixel_unique,(pixel_hist+10000)**(1/3)]
        pixel_range=pixel_unique[-1]-pixel_unique[0]+1
        if len(pixel_unique)<=pixel_range and pixel_range<=MASK_COLOR_LIMIT:
            attribute="MASK"
        else:
            attribute="CT"
        #ここからはRTSS専用の処理
        #RTSSを正確に視覚化することが目的なので
        #dicom_rt2maskで行っているxy座標の丸め込み？とは逆の処理をして、描画する画像の座標を正確なものにする
        #こうすることで輪郭をそのまま重ねることができるようになる
        #最後に読み込んだDcmDataから画像サイズの情報を参照する←同じシリーズならみんな同じだろうという仮定の下
        x_min=DcmData.ImagePositionPatient[0]
        x_max=x_min+DcmData.Columns*DcmData.PixelSpacing[1]#pixelspacingは一つ目が腹背方向、２つ目が左右方向
        y_min=DcmData.ImagePositionPatient[1]
        y_max=y_min+DcmData.Rows*DcmData.PixelSpacing[0]
        z_min=index2position[0]
        z_max=index2position[1]
        #CTVolumeのプロパティ
        self.ctvolume=ctvolume
        self.p2i=position2index#実際の位置からインデックスへの変換dict
        self.i2p=index2position#インデックスから実際の位置への変換dict
        self.hist=hist#ヒストグラム
        self.attribute=attribute#"CT" or "MASK"
        self.X_range=(x_min,x_max)
        self.Y_range=(y_min,y_max)
        self.Z_range=(z_min,z_max)
        self.vmin=hist[0][0]
        self.vmax=hist[0][-1]
        print("CT読み込み完了")
    def get(self,index):
        return self.ctvolume[index]
class RTSS:
    def __init__(self,rtss_filepath,index2position_dict,position2index_dict):
        #読み込む
        rtss=dicom.dcmread(rtss_filepath)
        structures={}
        for roi in rtss.StructureSetROISequence:
            structures[roi.ROINumber]=roi.ROIName
        
        contours={}
        for contour in rtss.ROIContourSequence:
            #iは色決定に使う
            #このcontourの組織名を取得
            structure=structures[contour.ReferencedROINumber]
            if not hasattr(contour,"ContourSequence"):
                continue
            contours[structure]={}
            contours[structure]["ROINumber"]=contour.ReferencedROINumber
            points={}
            for c in contour.ContourSequence:
                if c.ContourGeometricType!="CLOSED_PLANAR":#閉じていない輪郭はスキップ
                    continue
                contour_data=c.ContourData
                x=[float(x) for x in contour_data[0::3]]
                y=[float(y) for y in contour_data[1::3]]
                z=float(contour_data[2])
                xy=list(zip(x,y))
                xy.append(xy[0])#視点と終点をつなげる
                #同じz座標に同じ臓器の輪郭がある場合がある
                #例えば精嚢とか
                if z not in points:
                    points[z]=[]
                points[z].append(xy)#[[(x,y),(x,y),(x,y)...],]
            #これは表示に使わないしいらないかも
            #contours[structure]["points"]=points

            #表示用のPathを作成
            paths={}
            for z,p in points.items():
                _all_paths=[]
                _all_codes=[]
                for i,c in enumerate(p):
                    codes=np.ones(len(c))*Path.LINETO
                    codes[0]=Path.MOVETO
                    codes[-1]=Path.CLOSEPOLY
                    _all_paths.append(c)
                    _all_codes.append(codes)
                path=Path(np.concatenate(_all_paths),np.concatenate(_all_codes))
                paths[z]=path#z座標をkeyとするxy座標
            contours[structure]["paths"]=paths
            #輪郭更新の際に必要になるオブジェクトの場所を確保
            #<class 'matplotlib.patches.PathPatch'>
            contours[structure]["pathpatch"]=None
        #countoursを並び替えたい
        contours={ structure:contour for structure,contour in sorted(contours.items(),key=lambda x:x[1]["ROINumber"])}
        colors=colormap(len(contours),ALPHA=0.15)
        for structure_contour,color in zip(contours.values(),colors):
            structure_contour["ec"]=color[0:3]
            structure_contour["fc"]=color
        """
        contours=strucureName
                    ├points={z=1:[[(x,y),...],[(x,y),...]],z=2:}
                    ├Paths={z=1:path,z=2:path,...}
                    ├ec=(R,G,B)
                    ├fc=(R,G,B,a)
                    ├pathpatch <class 'matplotlib.patches.PathPatch'>
        """
        self.contours=contours
        self.i2p=index2position_dict
        self.p2i=position2index_dict
        """
        for k,v in self.i2p.items():
            print(k,v)
        """
        print("RTSS読み込み完了")
    def get(self,i,structure):
        #指定した組織のインデックスに対応する輪郭PATHを取り出す
        position=self.i2p[i]
        paths=self.contours[structure]["paths"]
        path=paths.get(position,Path([[0,0],[0,0]],[Path.MOVETO,Path.CLOSEPOLY]))
        return path
    
    def get_Range(self,structure,):
        #2025/06/13 頭から足にかけて+ →　-とポジションの値が変化する
        #つまり、head_zは最大値、tail_zは最小値となる
        z_list=self.contours[structure]["paths"].keys()
        head_z=max(z_list)
        tail_z=min(z_list)
        head_index=self.p2i[head_z]
        tail_index=self.p2i[tail_z]
        return (head_z,tail_z,head_index,tail_index)
