import json
import pandas as pd
import streamlit as st
import os
from scipy.stats import zscore
from scipy.signal import savgol_filter
import plotly.express as px


st.set_page_config(layout="wide")
st.title("Auto Cutting Tool")

if "button_clicked" not in st.session_state:
    st.session_state.button_clicked = False


def callback():
    st.session_state.button_clicked = True


@st.cache
def load_data():
    dataframe = pd.read_csv(os.path.join(r"C:\Users\samuello\Downloads\III\2022專案\韌性\data", "data.csv"))
    dataframe = dataframe[860000: 930000]
    return dataframe


data = load_data()
cols = data.columns

st.markdown("#### 主要參數設定")

with st.expander("主要參數設定", expanded=True):

    col1, col2, col3 = st.columns(3)

    with col1:
        target_name = st.select_slider("資料欄位名稱(如電流等資料欄位)", cols, cols[1])

    with col2:
        window_length = st.slider("過濾器窗格長度(過濾訊號用，越高越擬合原始資料)", 11, 101, 81, 2)

    with col3:
        polyorder = st.slider("過濾器冪次(過濾訊號用，越高越擬合原始資料)", 2, 10, 6, 1)

    col1, col2, _ = st.columns(3)

    with col1:
        threshold = st.number_input("閥值(擷取資料用，依實際需要調整)", -100.0, 100.0, 0.0, 0.1)

    with col2:
        frequency = st.number_input("擷取頻率(資料每秒筆數)", 10, 1000, 500, 1)

idx_list = []

if st.button("轉換資料!", on_click=callback) or st.session_state.button_clicked:

    data_ct = list(data[target_name])

    st.markdown("#### 原始資料")
    st.line_chart(data_ct)

    data_sf = savgol_filter(data_ct, window_length, polyorder)
    data_zscore = zscore(data_sf)

    st.markdown("#### 處理後資料")
    st.line_chart(data_zscore)

    st.success("處理前後圖像繪製完成!")

    st.markdown("#### 自動標記")

    i = 0
    state = "not working"

    while i < len(data_ct):
        z_score = data_zscore[i]

        if (z_score > threshold) & (state == "not working"):
            idx_list.append(i)
            state = "working"
        elif (z_score <= threshold) & (state == "working"):
            if i - idx_list[-1] > 1000:
                idx_list.append(i)
                state = "not working"
        i = i + 1

    data_zscore = pd.DataFrame(data_zscore, columns=["z-score"])
    data_zscore["index"] = data_zscore.index
    fig = px.line(data_zscore, x="index", y="z-score")
    idx = 0
    while idx < len(idx_list):
        fig.add_vrect(x0=idx_list[idx], x1=idx_list[idx + 1])
        idx = idx + 2
    st.plotly_chart(fig, use_container_width=True)

    st.success("自動標記完成!(黑框為資料擷取範圍)")

    idx = 0
    lst = []
    while idx < len(idx_list):
        lst.append(idx_list[idx + 1] - idx_list[idx])
        idx = idx + 2

    st.markdown("#### 次要參數設定")

    with st.expander("次要參數設定", expanded=True):

        col1, col2, col3 = st.columns(3)

        with col1:
            data_length = st.number_input("資料長度(頻域分析用，資料長度需相同)", min(lst), max(lst), min(lst), 1)

        with col2:
            use_data_length = st.checkbox("使用統一資料長度(勾選則套用左側資料長度設定值)")

        with col3:
            file_format = st.radio("下載格式", ["JSON", "CSV"], 0)

    if st.button("擷取資料!"):

        key_idx = 0
        idx = 0
        output_data = {}
        output_data_lst = []
        while idx < len(idx_list):
            if not use_data_length:
                output_data[key_idx] = data_ct[idx_list[idx]: idx_list[idx + 1]]
            else:
                output_data[key_idx] = data_ct[idx_list[idx]: idx_list[idx] + data_length]
            idx = idx + 2
            key_idx = key_idx + 1

        st.success("擷取資料完成，若有需要下載檔案請按下方按紐!")

        if file_format == "JSON":
            output_data_string = json.dumps(output_data)
            st.download_button("檔案下載(JSON)", output_data_string, "output-data.json", "application/json")
        elif file_format == "CSV":
            output_data = pd.DataFrame.from_dict(output_data, orient="index")
            st.download_button("檔案下載(CSV)", output_data.to_csv(), "output-data.csv", "text/csv")

