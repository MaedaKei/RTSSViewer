from RTSSViewerFunctions_v10 import RTSSViewerBase
from RTSSViewerFunctions_v10 import Function_Balance_Control
from RTSSViewerFunctions_v10 import ImageToneCorrection #CT画像の階調機能
from RTSSViewerFunctions_v10 import ImageSlideShow #スライドショー機能
from RTSSViewerFunctions_v10 import ImageZoomPan
from RTSSViewerFunctions_v10 import ROISelecter #ROI一覧表示＆選択


import argparse

def RTSSViewArguments(args_list=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("CTdirpath",type=str,help="CTvolumeがあるディレクトリパス")
    parser.add_argument("RTSSfilepath",type=str,help="RTSSfileのパス")
    parser.add_argument("--CT_gray_range","-cgr",type=int,nargs=2,default=[-180,180],help="CT画像の画素値の範囲の初期値を設定できる(起動後も変更可能)")
    
    args=parser.parse_args(args_list)
    return args

def RTSSViewer(args):
    need_ROWs=RTSSViewerBase.need_ROWs+ \
        ImageToneCorrection.need_ROWs+ \
        ImageSlideShow.need_ROWs+ \
        ROISelecter.need_ROWs
    
    base=RTSSViewerBase(args,need_ROWs)
    fbc=Function_Balance_Control(base)
    imagetonecorrection=ImageToneCorrection(base,fbc)
    imageslideshow=ImageSlideShow(base,fbc)
    imagezoompan=ImageZoomPan(base,fbc)
    roiselecter=ROISelecter(base,fbc)
    base.show()
if __name__=="__main__":
    args=RTSSViewArguments()
    RTSSViewer(args)