# 改良v1巢狀按鈕設計的痛點，以先設定完所有參數後再進行資料切割

# 引入套件
import json
import pandas as pd
import streamlit as st
import os
from scipy.stats import zscore
from scipy.signal import savgol_filter
import plotly.express as px

# 設定streamlit網頁
st.set_page_config(layout="wide")
st.title("Auto Cutting Tool")


# 上傳資料後，存入快取中，避免每重整一次就讀一次檔
@st.cache
def load_data():
    dataframe = pd.read_csv(os.path.join(r"C:\Users\samuello\Downloads\III\2022專案\韌性\data", "data.csv"))
    dataframe = dataframe[860000: 930000]
    return dataframe


# 讀取資料與欄位名稱
data = load_data()
cols = data.columns

st.markdown("#### 主要參數設定")

# 以滑動條設定主要參數
with st.expander("主要參數設定", expanded=True):

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        target_name = st.select_slider("資料欄位名稱(如電流等資料欄位)", cols, cols[1])

    with col2:
        window_length = st.slider("過濾器窗格長度(過濾訊號用，越高越擬合原始資料)", 11, 101, 81, 2)

    with col3:
        polyorder = st.slider("過濾器冪次(過濾訊號用，越高越擬合原始資料)", 2, 10, 6, 1)

    with col4:
        threshold = st.number_input("閥值(擷取資料用，依實際需要調整)", -100.0, 100.0, 0.0, 0.1)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        frequency = st.number_input("擷取頻率(資料每秒筆數)", 10, 1000, 500, 1)

    with col2:
        data_length = st.number_input("資料長度(頻域分析用，資料長度需相同)", 0, 10000, 1500, 1)

    with col3:
        use_data_length = st.checkbox("使用統一資料長度(勾選則套用左側資料長度設定值)")

    with col4:
        file_format = st.radio("下載格式", ["JSON", "CSV"], 0)

# 記錄切割後資料的起始索引值列表
idx_list = []

# 主要參數設定完後，點擊按鈕開始資料切割
if st.button("開始轉換！"):

    # 對目標參數資料過濾並計算zscore；各資料點的zscore存入變數data_zscore
    data_ct = data[target_name]
    sf = savgol_filter(data_ct, 81, 6)
    data_zscore = zscore(sf)

    # 顯示原始與處理後的圖像
    st.markdown("#### 原始資料")
    st.line_chart(data_ct)

    st.markdown("#### 處理後資料")
    st.line_chart(data_zscore)

    st.success("處理前後圖像繪製完成！")

    st.markdown("#### 自動標記")

    # 初始化(為機台未開始運作之狀態)
    i = 0
    state = "not working"

    # 取目標參數資料之長度，切割出運作時資料之索引值
    while i < len(data_ct):

        z_score = data_zscore[i]

        # 若資料點的zscore超過警戒值，且機台狀態為未工作，則表示「機台已開始作動(開始生產)」
        if (z_score > threshold) & (state == "not working"):
            idx_list.append(i)
            state = "working"
        # 若資料點的zscore低於警戒值，且機台狀態為工作中、與機台開始作動時間差距1000個資料點以上(此差距量須依實際狀態調整)，
        # 則表示「機台已結束作動(結束生產)」
        elif (z_score <= threshold) & (state == "working"):
            if i - idx_list[-1] > 1000:
                idx_list.append(i)
                state = "not working"
        i = i + 1

    # 將data_zscore轉換成dataframe，並新增index欄位方便繪圖之用
    data_zscore_df = pd.DataFrame(data_zscore, columns=["z-score"])
    data_zscore_df["index"] = data_zscore_df.index

    # 繪製折線圖
    fig = px.line(data_zscore_df, x="index", y="z-score")

    # 於折線圖上繪製(標記)方框
    idx = 0
    while idx < len(idx_list):
        fig.add_vrect(x0=idx_list[idx], x1=idx_list[idx + 1])
        idx = idx + 2
    st.plotly_chart(fig, use_container_width=True)

    st.success("自動標記完成！(黑框為資料擷取範圍) 若有需要下載檔案請按下方按紐！")

    # 初始化(輸出資料初始格式為json)
    key_idx = 0
    idx = 0
    output_data = {}

    # 擷取每個切割後資料的起始索引值
    while idx < len(idx_list):
        # 不使用資料統一長度(輸出資料為機台運作之完整資料)
        if not use_data_length:
            output_data[key_idx] = (data_ct[idx_list[idx]: idx_list[idx + 1]]).to_list()
        # 使用資料統一長度(輸出資料可能包含少部分機台未作動之資料，但方便於資料頻域分析之用)
        else:
            output_data[key_idx] = data_ct[idx_list[idx]: idx_list[idx] + data_length]
        idx = idx + 2
        key_idx = key_idx + 1

    st.markdown("#### 檔案下載")

    # 檔案下載，目前支援格式：json、csv
    if file_format == "JSON":
        output_data_string = json.dumps(output_data)
        st.download_button("檔案下載(JSON)", output_data_string, "output-data.json", "application/json")
    elif file_format == "CSV":
        output_data = pd.DataFrame.from_dict(output_data, orient="index")
        st.download_button("檔案下載(CSV)", output_data.to_csv(), "output-data.csv", "text/csv")

