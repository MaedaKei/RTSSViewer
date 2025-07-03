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
        pax=args.CTdirpath.split('/')[-2]
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
        self.ImageZoom_FLAG=False
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
        self.ImageZoom_FLAG=(True if self.ax_selected==True and self.pressed_key=="control" else False)
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
        self.pressed_button=None
        self.function_balance_control()

class ImageToneCorrection:
    need_ROWs=0
    def __init__(self,base,Function_Balance_Control):
        self.ctvolume=base.ctvolume
        self.fig=base.fig
        self.img_table=base.img_table
        self.Function_Balance_Control=Function_Balance_Control
        self.fig.canvas.mpl_connect("button_press_event",self.ToneCorrection_activate_event)
        
        print(f"{self.__class__.__name__} Registerd !")

    def ToneCorrection_activate_event(self,event):
        if self.Function_Balance_Control.ImageToneCorrection_FLAG and event.button==3:
            hist=self.ctvolume.hist
            self.img_table=self.img_table
            self.tone_window_fig=plt.figure(num=self.__class__.__name__,figsize=(5,4),tight_layout=True,clear=True)
            self.tone_window_gs=gridspec.GridSpec(3,1,height_ratios=[20,0.5,0.5])
            hist_ax=self.tone_window_fig.add_subplot(self.tone_window_gs[0,0])
            self.center_slice_ax=self.tone_window_fig.add_subplot(self.tone_window_gs[1,0],sharex=hist_ax)
            self.range_slice_ax=self.tone_window_fig.add_subplot(self.tone_window_gs[2,0])
            hist_ax.plot(*hist,color="#000000")
            hist_ax.tick_params(labelleft=False)
            #現在の画素値範囲,元の画素値範囲
            current_lower,current_upper=self.img_table.norm.vmin,self.img_table.norm.vmax
            original_lower,original_upper=self.ctvolume.vmin,self.ctvolume.vmax
            #スライダーを動かして更新されるやつらは変数に入れておく
            self.value_text=hist_ax.set_title(f"[ {current_lower} ~ {current_upper} ]")
            self.lower_limit_line=hist_ax.axvline(current_lower,color="#FF0000",alpha=0.5)
            self.upper_limit_line=hist_ax.axvline(current_upper,color="#FF0000",alpha=0.5)
            self.center_slice=Slider(ax=self.center_slice_ax,label='center',valmin=original_lower,valmax=original_upper,
                                valinit=(current_lower+current_upper)/2,valstep=1,valfmt='%d',handle_style={'size':5})
            self.range_slice=Slider(ax=self.range_slice_ax,label='range',valmin=0,valmax=original_upper-original_lower,
                                valinit=current_upper-current_lower,valstep=1,valfmt='%d',handle_style={'size':5})
            self.center_slice.on_changed(self.slice_moved)
            self.range_slice.on_changed(self.slice_moved)
            plt.show()
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
            if event.button=="up":
                change_value=-1
            elif event.button=="down":
                change_value=1
            #この機能ではグローバルなし
            self.slicer.set_val((self.slicer.val+change_value)%self.slicer_length)
    
            #self.fig.canvas.draw_idle()
    #CTVolume一つだけ表示なので、スライス位置のリセットも不要

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
            self.Selected_ROI_counter["component"]=ax.set_title(f"Selecting : {self.Selected_ROI_counter["value"]}",fontdict={"fontsize":10})
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
        self.Selected_ROI_counter["component"].set_text(f"Selecting : {self.Selected_ROI_counter["value"]}")
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
        print(f"----------------------\n{self.Selected_ROI_counter["value"]} 種のROIを {save_filepath} に保存")