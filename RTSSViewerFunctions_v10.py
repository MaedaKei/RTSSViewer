from RTSSloaders import CTVolume,RTSS
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider,CheckButtons
from matplotlib import gridspec
#from matplotlib.path import Path
import matplotlib.patches as patches
import numpy as np
import os
import math

class RTSSViewerBase:
    need_ROWs=1#画像エリア
    def __init__(self,args,ax_rows):
        #CTvolumeの読み込み
        self.ctvolume=CTVolume(args.CTdirpath)
        #RTSSfileの読み込み
        self.rtss=RTSS(args.RTSSfilepath,self.ctvolume.i2p,self.ctvolume.p2i)
        #PAX抽出
        try:
            pax=args.CTdirpath.split('/')[-2]
        except:
            pax=""
        self.row_counter=0
        #パスも一応保存する
        self.CTdirpath=args.CTdirpath
        self.RTSSfilepath=args.RTSSfilepath
        """CT画像の表示"""
        volume_num=1
        height_ratios=np.ones(ax_rows)*0.3
        height_ratios[0]=30
        self.gs=gridspec.GridSpec(ax_rows,volume_num,height_ratios=height_ratios,hspace=0.01,wspace=0.05,top=0.97,bottom=0.01,right=0.99,left=0.01)
        self.fig=plt.figure(num=f"RTSSviewer [ {pax} ]",figsize=(7,7))
        mngr=plt.get_current_fig_manager()
        volume_n=volume_num-1
        self.img_ax=self.fig.add_subplot(self.gs[self.row_counter,volume_n])
        self.row_counter+=1
        self.img_ax.axis("off")
        #カラーマップの設定
        if self.ctvolume.attribute=="CT":
            cmap="gray"
            norm=None
        elif self.ctvolume.attribute=="MASK":
            cmap="gray"
            norm=None
        #透過度の設定
        alpha=1
        #extentの設定
        #left right bottom top
        extent=(self.ctvolume.X_range[0],self.ctvolume.X_range[1],self.ctvolume.Y_range[1],self.ctvolume.Y_range[0])
        initial_index=0
        self.title_text=self.img_ax.set_title(f"{initial_index}",fontdict={"fontsize":10})
        self.img_table=self.img_ax.imshow(
            self.ctvolume.get(initial_index),cmap=cmap,norm=norm,alpha=alpha,
            extent=extent
        )
        #CT画像なので、引数で指定した初期値を設定
        self.img_table.norm.vmin=min(args.CT_gray_range)
        self.img_table.norm.vmax=max(args.CT_gray_range)
        
        #self.pathpatch_dict={}#<class 'matplotlib.patches.PathPatch'> をまとめた辞書
        for structure in self.rtss.contours.keys():
            path=self.rtss.get(0,structure)
            ec=self.rtss.contours[structure]["ec"]
            fc=self.rtss.contours[structure]["fc"]
            self.rtss.contours[structure]["pathpatch"]=self.img_ax.add_patch(patches.PathPatch(path,ec=ec,fc=fc,lw=0.7))
            self.rtss.contours[structure]["pathpatch"].set(visible=False)
        #print(type(self.patch_dict[structure]))
        #pathpatchにはset_pathがあるらしい
        
    def show(self):
        plt.show()

class Function_Balance_Control:
    def __init__(self,base):
        self.fig=base.fig
        self.img_ax=base.img_ax

        #マウス位置の監視
        self.ax_selected=False
        self.selected_ax=None
        self.fig.canvas.mpl_connect("axes_enter_event",self.axes_enter_event)
        self.fig.canvas.mpl_connect("axes_leave_event",self.axes_leave_event)
        #ボタンの押下の可否
        self.pressed=False
        self.pressed_key=None
        self.fig.canvas.mpl_connect("key_press_event",self.key_press_event)
        self.fig.canvas.mpl_connect("key_release_event",self.key_release_event)
        self.ImageToneCorrection_FLAG=False
        self.ImageSlideShow_FlAG=True
        self.ImageZoomPan_FLAG=False
        self.ROIselecter_FLAG=False
    
    def function_balance_control(self):
        #諧調補正の起動
        #画像内で右クリックをする
        #画像内右クリックがほかの機能にも割り当てられれば、新しく条件を追加する必要がある
        self.ImageToneCorrection_FLAG=(True if self.ax_selected==True else False)
        self.ROISelecter_FLAG=(True if self.ax_selected==True else False)
        #マウスがグラフ内にあり、Ctrlボタンが押されているならimage_sliceはOFF
        #そのうち、ボタンが押されているならOFFという条件に難化するかも
        #このフラグはスライドショーに適用され、spaceボタンによる位置合わせには適用されない
        self.ImageSlideShow_FLAG=(False if self.ax_selected==True and self.pressed_key=="control" else True)
        #マウスがグラフ内にあり、Ctrlボタンが押されているならimage_sliceはON
        self.ImageZoomPan_FLAG=(True if self.ax_selected==True and self.pressed_key=="control" else False)
        #print("ImageToneCorrection",self.ImageToneCorrection_FLAG)
    def axes_enter_event(self,event):
        if event.inaxes==self.img_ax:
            self.ax_selected=True
            self.selected_ax=event.inaxes
        self.function_balance_control()
    def axes_leave_event(self,event):
        self.ax_selected=False
        self.selected_ax_number=None
        self.function_balance_control()
    def key_press_event(self,event):
        self.pressed=True
        self.pressed_key=event.key
        self.function_balance_control()
    def key_release_event(self,event):
        self.pressed=False
        self.pressed_key=None
        self.function_balance_control()

class ImageToneCorrection:
    need_ROWs=0
    def __init__(self,base,Function_Balance_Control):
        self.ctvolume=base.ctvolume
        self.fig=base.fig
        self.img_table=base.img_table
        self.Function_Balance_Control=Function_Balance_Control
        self.fig.canvas.mpl_connect("button_press_event",self.ToneCorrection_activate_event)
        """
        yの最大値を基にrange_step_tableを決定する
        """
        #まずは何段階＝画素値の整数部分が最大何桁か算出する
        self.step_level=math.floor(math.log(self.ctvolume.hist_x_max,10))+1
        self.range_step_table=[10**i for i in range(self.step_level)]
        print(self.range_step_table)
        self.range_step_threshold=self.ctvolume.hist_y_max/self.step_level

        self.center=None
        self.range=None
        print(f"{self.__class__.__name__} Registerd !")

    def ToneCorrection_activate_event(self,event):
        if self.Function_Balance_Control.ImageToneCorrection_FLAG and event.button==3:
            hist=self.ctvolume.hist
            self.img_table=self.img_table
            self.tone_window_fig=plt.figure(num=self.__class__.__name__,figsize=(5,4),clear=True)
            self.tone_window_gs=gridspec.GridSpec(1,1,left=0.05,right=0.95,top=0.9,bottom=0.1)
            hist_ax=self.tone_window_fig.add_subplot(self.tone_window_gs[0,0])
            hist_ax.plot(*hist,color="#000000")
            #hist_ax.tick_params(labelleft=False)
            hist_ax.set_xlim(self.ctvolume.hist_x_min,self.ctvolume.hist_x_max)
            hist_ax.set_ylim(self.ctvolume.hist_y_min,self.ctvolume.hist_y_max)
            hist_ax.set_xticks([self.ctvolume.hist_x_min,self.ctvolume.hist_x_max])
            ydatalist=[self.range_step_threshold*(i+1) for i in range(self.step_level)]
            hist_ax.set_yticks(ydatalist)
            hist_ax.set_yticklabels(self.range_step_table,fontdict={'fontsize':5})
            hist_ax.grid(axis='y',ydata=ydatalist)
            #現在の画素値範囲,元の画素値範囲
            current_lower,current_upper=self.img_table.norm.vmin,self.img_table.norm.vmax
            self.value_text=hist_ax.set_title(f"[ {current_lower:5.1f} ~ {current_upper:5.1f} ]")
            self.lower_limit_line=hist_ax.axvline(current_lower,color="#0000FF",alpha=0.5)
            self.upper_limit_line=hist_ax.axvline(current_upper,color="#FF0000",alpha=0.5)
            """
            self.center_slice=Slider(ax=self.center_slice_ax,label='center',valmin=original_lower,valmax=original_upper,
                                valinit=(current_lower+current_upper)/2,valstep=1,valfmt='%d',handle_style={'size':5})
            self.range_slice=Slider(ax=self.range_slice_ax,label='range',valmin=0,valmax=original_upper-original_lower,
                                valinit=current_upper-current_lower,valstep=1,valfmt='%d',handle_style={'size':5})
            self.center_slice.on_changed(self.slice_moved)
            self.range_slice.on_changed(self.slice_moved)
            """
            self.center=(current_upper+current_lower)/2
            self.range=(current_upper-current_lower)/2
            self.x=None
            self.change_target=False
            #マウス監視
            self.tone_window_fig.canvas.mpl_connect("axes_enter_event",self.axes_enter)
            self.tone_window_fig.canvas.mpl_connect("axes_leave_event",self.axes_leave)
            self.tone_window_fig.canvas.mpl_connect("button_press_event",self.button_press)
            self.tone_window_fig.canvas.mpl_connect("button_release_event",self.button_release)
            self.in_axes=False
            self.pressed_button=False
            #諧調用関数
            self.tone_window_fig.canvas.mpl_connect("motion_notify_event",self.center_change_set)
            self.tone_window_fig.canvas.mpl_connect("scroll_event",self.range_change_set)
            plt.show()
    
    def axes_enter(self,event):
        self.in_axes=True
        self.Check()
    
    def axes_leave(self,event):
        self.in_axes=False
        self.Check()
    
    def button_press(self,event):
        self.pressed_button=event.button
        self.x=event.xdata
        self.Check()
    
    def button_release(self,event):
        self.pressed_button=False
        self.x=None
        self.Check()
    
    def Check(self):
        if self.in_axes:
            if  (self.pressed_button==1) and ((self.center-self.range/2)<self.x and (self.x < self.center+self.range)):
                self.change_target='center'
            else:
                self.change_target='range'
        else:
            self.change_target=False
    
    def center_change_set(self,event):
        if self.change_target=='center':
            new_x=event.xdata
            diff_x=new_x-self.x
            #どちらかが下限、上限に達している場合は動かないようにする
            center=max(self.ctvolume.hist_x_min+self.range,min(self.center+diff_x,self.ctvolume.hist_x_max-self.range))
            if center!=self.center:
                self.center=center
                self.change_commit(center-self.range,center+self.range)
            self.x=new_x

    def range_change_set(self,event):
        if self.change_target=='range':
            #print("起動しているよ")
            _change_value=self.range_step_table[math.ceil(event.ydata/self.range_step_threshold)-1]
            if event.button=='up':#範囲拡大
                change_value=_change_value
            elif event.button=='down':#範囲縮小
                change_value=(-_change_value)
            
            #rangeが0以下にならないようにすることでlowerとupperの逆転が起こらないようにしている
            #また、上限を設けることで、rangeが大きくなりすぎることで画面に変更が見られない時間をなくす
            range=max(0,self.range+change_value)
            lower=max(self.ctvolume.hist_x_min,self.center-range)
            upper=min(self.center+range,self.ctvolume.hist_x_max)
            if self.img_table.norm.vmin!=lower or self.img_table.norm.vmin!=upper:
                #upperとlowerから今回の最終的な情報を更新
                self.center=(upper+lower)/2
                self.range=(upper-lower)/2
                self.change_commit(lower,upper)
    
    def change_commit(self,lower,upper):
        self.img_table.norm.vmin=lower
        self.img_table.norm.vmax=upper
        self.lower_limit_line.set_xdata([lower])
        self.upper_limit_line.set_xdata([upper])
        self.value_text.set_text(f"[ {lower:5.1f} ~ {upper:5.1f} ]")
        self.tone_window_fig.canvas.draw_idle()
        self.fig.canvas.draw_idle()
    
    """
    def slice_moved(self,val):
        half_range=self.range_slice.val/2
        min=self.center_slice.val-half_range
        max=self.center_slice.val+half_range
        self.img_table.norm.vmin=min
        self.img_table.norm.vmax=max
        self.value_text.set_text(f"[ {min} ~ {max} ]")
        self.lower_limit_line.set_xdata([min,min])
        self.upper_limit_line.set_xdata([max,max])
        self.tone_window_fig.canvas.draw_idle()
        self.fig.canvas.draw_idle()
    """

class ImageSlideShow:
    need_ROWs=1
    def __init__(self,base,Function_Balance_Control):
        self.ctvolume=base.ctvolume
        self.rtss=base.rtss
        self.fig=base.fig
        self.title_text=base.title_text
        self.img_table=base.img_table
        self.Function_Balance_Control=Function_Balance_Control
        
        self.slicer_length=len(base.ctvolume.ctvolume)
        volume_num=1
        volume_n=volume_num-1
        ax=base.fig.add_subplot(base.gs[base.row_counter,volume_n])
        slicer=Slider(
            ax=ax,label=None,valinit=0,valmin=0,valmax=self.slicer_length-1,
            valfmt="%d",valstep=1,orientation="horizontal",
            handle_style={"size":5}
        )
        slicer.on_changed(self.slicer_changed)
        self.slicer=slicer
        base.row_counter+=1

        self.fig.canvas.mpl_connect("scroll_event",self.slicer_scroll_event)
        #現時点でWindowの選択にかかわらず動かすことができない→つまり、マウスを動かすことは確定しているため今はOFFにする
        #self.fig.canvas.mpl_connect("key_press_event",self.slicer_press_event)
        print(f"{self.__class__.__name__} Registerd !")
    
    def slicer_changed(self,dammy_args):
        #画像変更
        self.img_table.set_data(self.ctvolume.get(self.slicer.val))
        self.title_text.set_text(f"{self.slicer.val}")
        #輪郭変更
        for structure,contour in self.rtss.contours.items():
            target_pathpatch=contour["pathpatch"]
            target_pathpatch.set_path(self.rtss.get(self.slicer.val,structure))
        self.fig.canvas.draw_idle()
    
    def slicer_scroll_event(self,event):
        if self.Function_Balance_Control.ImageSlideShow_FLAG:
            if event.button=="down":
                change_value=-1
            elif event.button=="up":
                change_value=1
            #この機能ではグローバルなし
            self.slicer.set_val((self.slicer.val+change_value)%self.slicer_length)
    
            #self.fig.canvas.draw_idle()
    #CTVolume一つだけ表示なので、スライス位置のリセットも不要
class ImageZoomPan:
    def __init__(self,base,Function_Balance_Control):
        self.ctvolume=base.ctvolume
        self.rtss=base.rtss
        self.fig=base.fig
        self.img_ax=base.img_ax
        self.img_table=base.img_table
        self.Function_Balance_Control=Function_Balance_Control
        """
        print(type(self.fig))
        print(type(self.fig.canvas))
        print(type(self.img_table))
        """
        #画像サイズの情報を保持
        self.imagesize_info={key:value for key,value in zip(['left','right','bottom','top'],self.img_table.get_extent())}
        self.OriginalWidth=self.imagesize_info['right']-self.imagesize_info['left']
        self.OriginalHeight=self.imagesize_info['bottom']-self.imagesize_info['top']
        #画像の描画位置に関する情報の初期化
        self.scale_step_range=0.1
        self.minscale=1
        self.maxscale=8
        self.imagescale=1
        self.left=0
        self.top=0
        self.width=self.OriginalWidth
        self.height=self.OriginalHeight
        #マウスイベントを追加
        #Zoom or Pan
        self.Function_Flag='ImageZoom'
        self.fig.canvas.mpl_connect("button_press_event",self.mouse_left_press)
        self.fig.canvas.mpl_connect("button_release_event",self.mouse_left_release)
        #拡大縮小
        self.fig.canvas.mpl_connect("scroll_event",self.ImageZoom)
        self.fig.canvas.mpl_connect("button_press_event",self.ImageZoomReset)
        #移動
        self.mouse_x=None
        self.mouse_y=None
        self.fig.canvas.mpl_connect("motion_notify_event",self.ImagePan)

        print(f"{self.__class__.__name__} Registerd !")
    def mouse_left_press(self,event):
        if self.Function_Balance_Control.ImageZoomPan_FLAG and event.button==1:
            self.mouse_x=event.xdata
            self.mouse_y=event.ydata
            self.Function_Flag='ImagePan'
    
    def mouse_left_release(self,event):
        if self.Function_Balance_Control.ImageZoomPan_FLAG:
            self.mouse_x=None
            self.mouse_y=None
            self.Function_Flag='ImageZoom'
    
    def ImageZoom(self,event):
        #動作できる状態か
        if self.Function_Balance_Control.ImageZoomPan_FLAG and self.Function_Flag=='ImageZoom':
            #print(f"( {event.xdata} , {event.ydata} )")
            if event.button=='down':
                change_scale=-1*self.scale_step_range
            elif event.button=='up':
                change_scale=self.scale_step_range
            
            #描画サイズ決定
            #ただし、実際の座標系から0～512みたいな座標系に変換してから処理する
            x=event.xdata-self.imagesize_info['left']
            y=event.ydata-self.imagesize_info['top']
            #print(x,y)
            pre_scale=self.imagescale
            new_scale=min(self.maxscale,max(pre_scale+change_scale,self.minscale))#スケールは1～5にしておく
            if pre_scale==new_scale:
                #縮尺変化なしなので終了
                return
            
            zoomwidth=self.OriginalWidth/new_scale
            zoomheight=self.OriginalHeight/new_scale
            left=self.left
            top=self.top
            zoomleft=((new_scale-pre_scale)*x+pre_scale*self.left)/new_scale
            zoomleft=max(0,min(zoomleft,self.OriginalWidth-zoomwidth))
            zoomtop=((new_scale-pre_scale)*y+pre_scale*self.top)/new_scale
            zoomtop=max(0,min(zoomtop,self.OriginalHeight-zoomheight))
            #更新
            self.left=zoomleft
            self.top=zoomtop
            self.imagescale=new_scale
            self.width=zoomwidth
            self.height=zoomheight
            #再描画
            left=zoomleft+self.imagesize_info['left']
            right=left+zoomwidth
            top=zoomtop+self.imagesize_info['top']
            bottom=top+zoomheight
            self.img_ax.set_xlim(left,right)
            self.img_ax.set_ylim(bottom,top)
            """
            self.img_table.set(extent=(
                self.zoomleft,
                self.zoomleft+zoomwidth,
                self.zoomtop+zoomheight,
                self.zoomtop
            ))
            """
            self.fig.canvas.draw_idle()
    def ImageZoomReset(self,event):
        #print(self.Function_Balance_Control.ImageZoomPan_FLAG,self.Function_Flag,event.key)
        if self.Function_Balance_Control.ImageZoomPan_FLAG and self.Function_Flag=='ImageZoom' and event.button==2:
            self.imagescale=1
            self.left=0
            self.top=0
            self.width=self.OriginalWidth
            self.height=self.OriginalHeight
            #これを-256～256みたいな座標系に変換して値をセット
            self.img_ax.set_xlim(self.imagesize_info['left'],self.imagesize_info['right'])
            self.img_ax.set_ylim(self.imagesize_info['bottom'],self.imagesize_info['top'])
            self.fig.canvas.draw_idle()
    def ImagePan(self,event):
        #左クリックがされている間
        if self.Function_Balance_Control.ImageZoomPan_FLAG and self.Function_Flag=='ImagePan' and event.button==1:
            new_mouse_x=event.xdata
            new_mouse_y=event.ydata
            x_dif=new_mouse_x-self.mouse_x
            y_dif=new_mouse_y-self.mouse_y
            panleft=self.left-x_dif
            panleft=max(0,min(panleft,self.OriginalWidth-self.width))
            pantop=self.top-y_dif
            pantop=max(0,min(pantop,self.OriginalHeight-self.height))
            draw_idle_FLAG=False
            if panleft==self.left:
                self.mouse_x=new_mouse_x
            else:
                self.left=panleft
                left=panleft+self.imagesize_info['left']
                right=left+self.width
                self.img_ax.set_xlim(left,right)
                draw_idle_FLAG=True
            if pantop==self.top:
                self.mouse_y=new_mouse_y
            else:
                self.top=pantop
                top=pantop+self.imagesize_info['top']
                bottom=top+self.height
                self.img_ax.set_ylim(bottom,top)
                draw_idle_FLAG=True
            if draw_idle_FLAG:
                self.fig.canvas.draw_idle()

class ROISelecter:
    need_ROWs=0
    def __init__(self,base,Function_Balance_Control):
        self.ctvolume=base.ctvolume
        self.rtss=base.rtss
        self.fig=base.fig
        self.img_table=base.img_table
        self.Function_Balance_Control=Function_Balance_Control

        self.output_path=os.path.dirname(base.RTSSfilepath)
        self.fig.canvas.mpl_connect("button_press_event",self.ROIselecter_activate_event)
        key_list=list(self.rtss.contours.keys())
        #ROI_kinds=len(self.key_list)
        self.ROIName_maxlength=len(max(key_list,key=lambda x:len(x)))
        #現在の予定では、ROIごとにindex, pre_status, evacuateの3つ
        self.ROIs_Info={roiname:{"index":(0,0),"pre_status":False,"evacuated_status":False} for roiname in key_list}
        self.Selected_ROI_counter={"value":0,"compornent":None}
        print(f"{self.__class__.__name__} Registerd !")
    
    def ROIselecter_activate_event(self,event):
        if self.Function_Balance_Control.ROISelecter_FLAG and event.button==3:
            key_list=list(self.ROIs_Info.keys())
            ROI_kinds=len(key_list)
            max_length=self.ROIName_maxlength
            columns_num=math.ceil(ROI_kinds/30)
            #columns_num=2
            #window用意
            self.ROISelectWindow_fig=plt.figure(f"{ROI_kinds} ROIs",figsize=(0.1*max_length*columns_num+0.5,0.7+ROI_kinds/(columns_num*5)))
            gs=gridspec.GridSpec(1,columns_num,hspace=0,wspace=0,top=0.95,bottom=0,right=1,left=0)
            #配置決定
            base_rows_num=ROI_kinds//columns_num
            surplus_num=ROI_kinds%columns_num
            rows_num_list=[base_rows_num for _ in range(columns_num)]
            for i in range(surplus_num):
                rows_num_list[i]+=1
            #もし10個を３分割だったら[4,3,3]となっている
            label_list=[]
            visible_list=[]
            color_list=[]
            self.label2index=dict()
            self.CheckButton_list=[]
            sn=0
            i=0#行(0~)
            j=0#列(0~)
            while sn<ROI_kinds:
                structure_name=key_list[sn]
                contour=self.rtss.contours[structure_name]
                label_list.append(structure_name)
                visible=contour["pathpatch"].get_visible()
                visible_list.append(visible)
                color_list.append(contour["ec"])
                #チェックリストの位置、現在の状態、記憶要請を受けているかを保持させる
                #self.ROIs_Info[structure_name]={"index":(i,j),"pre_status":visible}
                self.ROIs_Info[structure_name]["index"]=(i,j)
                self.ROIs_Info[structure_name]["pre_status"]=visible
                sn+=1
                i+=1
                if i==rows_num_list[j]:
                    #必要数溜まったので描画する
                    ax=self.ROISelectWindow_fig.add_subplot(gs[0,j])
                    checkbutton=CheckButtons(
                        ax=ax,labels=label_list,
                        actives=visible_list,
                        frame_props={"edgecolor":color_list},
                        label_props={"fontsize":[10 for _ in range(len(label_list))]}
                    )
                    checkbutton.on_clicked(self.ROI_clicked)
                    self.CheckButton_list.append(checkbutton)
                    #リストとiを初期化
                    label_list=[]
                    visible_list=[]
                    color_list=[]
                    i=0
                    j+=1
            #最後のaxにCounterタイトルをセット
            self.Selected_ROI_counter["component"]=ax.set_title(f"Selecting : {self.Selected_ROI_counter['value']}",fontdict={'fontsize':10})
            #主にリセット用
            #spaceキーによる一括選択機能
            #Excelにあるフィルターの機能を参考に作成する
            #全てにチェックがされている状態ではリセットモード
            #2025/06/16現在　
            # 
            # 何もチェックされていない場合はすべてチェックとなる
            self.ROISelectWindow_fig.canvas.mpl_connect("key_press_event",self.space_pressed_event)
            # チェック保存機能
            self.ROISelectWindow_fig.canvas.mpl_connect("key_press_event",self.M_pressed_event)
            self.ROISelectWindow_fig.canvas.mpl_connect("close_event",self.close)
            plt.show()
    
    def ROI_clicked(self,label):
        #必ず変更が起こるときに呼び出されるようにする
        #一括変更の際はそちら側でチェックすること
        target_pathpatch=self.rtss.contours[label]["pathpatch"]
        #Checkbuttonの状態を取得
        i,j=self.ROIs_Info[label]["index"]
        status=self.CheckButton_list[j].get_status()[i]
        target_pathpatch.set(visible=status)
        self.ROIs_Info[label]["pre_status"]=status
        #カウント数書き換え処理
        count_change=(1 if status else -1)
        self.Selected_ROI_counter["value"]+=count_change
        #セレクトウィンドウの再描画も必要になった
        self.Selected_ROI_counter["component"].set_text(f"Selecting : {self.Selected_ROI_counter['value']}")
        self.ROISelectWindow_fig.canvas.draw_idle()
        #メインウィンドウの再描画
        self.fig.canvas.draw_idle()
    def M_pressed_event(self,event):
        # ctrl+m で記憶　ボタン２つ同時押しにすることで不意の記憶上書きを防ぐ
        # m で吐き出し
        text=[]
        if event.key=="ctrl+m":
            #記憶モード
            for roiname,ri in self.ROIs_Info.items():
                ri["evacuated_status"]=ri["pre_status"]
                if ri["evacuated_status"]:
                    text.append(roiname)
            print("----------------------")
            print(f"選択状態を記憶しました。( {len(text)} )")
            print('\n'.join(text))
            print("----------------------")
        elif event.key=="m":
            #復元モード
            for ri in self.ROIs_Info.values():
                if ri["pre_status"]!=ri["evacuated_status"]:#変更必要なら
                    i,j=ri["index"]
                    self.CheckButton_list[j].set_active(i,ri["evacuated_status"])
    def space_pressed_event(self,event):
        if event.key==" ":
            #現在のチェック状況を確認
            """
            All_Checked=True
            for ri in self.ROIs_Info.values():
                if not ri["pre_status"]:#チェックされていなければ
                    All_Checked=False
                    break
            """
            All_Selected=(len(self.ROIs_Info)==self.Selected_ROI_counter["value"])

            #All_SelectedがTrueならリセットモード→Falseをセット
            #All_SelectedがFalseなら全選択モード→Trueをセット
            #つまり、not All_Selectedをセットすればよい
            #状態が異なるROIだけセットする　→　pre_status!=(not All_Selected) →　pre_status==All_Selected
            for ri in self.ROIs_Info.values():
                i,j=ri["index"]
                pre_status=ri["pre_status"]
                if pre_status==All_Selected:
                    self.CheckButton_list[j].set_active(i,(not All_Selected))
        
    def close(self,event):
        #選択したROIの情報を保存して閉じる
        save_filepath=os.path.join(self.output_path,"CheckedROINames.csv")
        print(f"\n----------------------")
        with open(save_filepath,"w") as f:
            for ROIName,ri in self.ROIs_Info.items():
                if ri["pre_status"]:
                    text=f"{ROIName}, {', '.join([str(v) for v in self.rtss.get_Range(ROIName)])}\n"
                    print(text,end="")
                    f.write(f"{text}")
        print(f"----------------------\n{self.Selected_ROI_counter['value']} 種のROIを {save_filepath} に保存")