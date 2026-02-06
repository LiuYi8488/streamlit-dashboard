# app.py － Streamlit 版骨架（可直接部署到 Streamlit Cloud）
import os
import re
from pathlib import Path
import streamlit as st

# 如果之後你把 finder.py / detector.py 放進同一個 repo，就能 import 成功
try:
    from config import ROOTS, SEARCH_MAX_DEPTH  # 可選
    from finder import locate_files            # 可選
    from detector import detect_vector, detect_gamma  # 可選
except Exception:
    ROOTS = {}
    SEARCH_MAX_DEPTH = 0
    locate_files = None
    detect_vector = None
    detect_gamma = None

st.set_page_config(page_title="ZBOM/Zcau Finder + 判讀", page_icon="🔎", layout="wide")
st.title("ZBOM / Zcau Finder + 判讀")

with st.sidebar:
    st.markdown("**環境設定**")
    VECTOR_MAP_PATH = st.text_input("Vector 對照表路徑（雲端或相對路徑）", "vector_maps.xlsx")
    GAMMA_MAP_PATH  = st.text_input("Gamma 對照表路徑（雲端或相對路徑）", "gamma_maps.xlsx")
    DEBUG_TO_USER_DEFAULT = st.checkbox("顯示除錯訊息", value=False)

col1, col2, col3 = st.columns([1,1,1])
with col1:
    model = st.selectbox("機種", ["Vector", "Gamma", "Speed"], index=0)
with col2:
    six = st.text_input("FCID（6碼）", placeholder="例：262174")
with col3:
    go = st.button("搜尋", use_container_width=True)

def show_result_block(title, det: dict|None):
    if not isinstance(det, dict):
        st.info("（暫無結果）")
        return
    st.subheader(f"[{title} 判讀]")
    result_text = det.get("result") or "（無結果）"
    st.markdown(f"**結果：** :green[{result_text}]")
    with st.expander("原始結果", expanded=False):
        st.json(det, expanded=False)

if go:
    if not six or not re.fullmatch(r"\d{6}", str(six).strip()):
        st.error("請輸入正確格式：6 位數字（例：262174）")
        st.stop()

    # ===== A. 若你還沒把 finder/detector 放入 repo，先示範流程 =====
    if locate_files is None:
        st.warning("尚未整合 finder/detector；這裡先示範顯示輸入參數與假資料。")
        st.write({"machine": model, "FCID": six})
        st.info("把 finder.py / detector.py 放進 repo 後，我會幫你接回真正邏輯。")
        st.stop()

    # ===== B. 真正流程（當你把 finder/detector 放進 repo 後打開） =====
    try:
        found = locate_files(ROOTS, six, machine=model)
    except Exception as e:
        st.error(f"搜尋時發生錯誤：{e}")
        st.stop()

    if not found:
        msg = f"[{model}] 找不到符合 {six} 的檔案。"
        if SEARCH_MAX_DEPTH == 0:
            msg += "（目前僅掃『根目錄第一層』；請確認『機種』是否選對。）"
        st.warning(msg)
        st.stop()

    zbom = found.get("zbom_pdf")
    zcau = found.get("zcau_xls")

    st.markdown("#### 基本資訊")
    st.write({"機種": found.get("machine") or model, "FCID": six})

    st.markdown("#### 找到的檔案")
    st.code(zbom or "(ZBOM PDF 未找到)")
    st.code(zcau or "(Zcau Excel 未找到)")

    try:
        if model == "Vector" and zbom and detect_vector:
            det = detect_vector(zbom, maps_path=VECTOR_MAP_PATH, debug=DEBUG_TO_USER_DEFAULT)
            show_result_block("Vector", det)
        elif model == "Gamma" and detect_gamma:
            if not zbom or not zcau:
                st.info("[Gamma 判讀] 需同時找到 PDF 與 BOM（Excel）才能判讀。")
            else:
                det = detect_gamma(zbom, zcau, maps_path=GAMMA_MAP_PATH, debug=DEBUG_TO_USER_DEFAULT)
                show_result_block("Gamma", det)
        else:
            st.info("此機種暫未定義或檔案不足。")
    except Exception as e:
        st.error(f"判讀時發生錯誤：{e}")
