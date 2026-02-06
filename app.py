# streamlit_app.py
import streamlit as st
import re
import json
from pathlib import Path

# ---- 你現有的模組（需能在無 Flask 環境下 import）----
from config import ROOTS, SEARCH_MAX_DEPTH  # 若不再用 ROOTS，可先保留
from finder import locate_files
from detector import detect_vector, detect_gamma

# ====== 你原來的映射與 log 路徑：改成 repo 相對路徑或 st.secrets ======
# 建議把 Excel map 檔放到 repo 的 data/ 目錄
VECTOR_MAP_PATH = Path("data/TypeMap.xlsx").as_posix()
GAMMA_MAP_PATH  = Path("data/maps.xlsx").as_posix()
DEBUG_LOG_PATH  = Path("logs/debug.log").as_posix()  # 在 Streamlit Cloud 可寫入 ./logs

# 頁面標題與樣式
st.set_page_config(page_title="ZBOM / Zcau Finder + 判讀 (Streamlit)", layout="wide")
st.markdown("""
<style>
.result-pill{
  display:inline-block;padding:8px 14px;border-radius:999px;
  background:linear-gradient(135deg, #00b894, #00cec9);
  color:white;font-weight:800;letter-spacing:.3px;
  box-shadow:0 8px 18px rgba(0,206,201,.25);
  border:1px solid rgba(255,255,255,.35);
}
.path-text{font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;}
</style>
""", unsafe_allow_html=True)

st.title("ZBOM / Zcau Finder (Streamlit 版)")
st.caption("v1.3 – 將 Dash 版改寫為 Streamlit 版，便於在 Streamlit Cloud 部署")

# ========== 篩選條件 ==========
col1, col2, col3 = st.columns([1,1,1])
with col1:
    model = st.selectbox("機種", ["Vector", "Gamma", "Speed"], index=0)
with col2:
    six = st.text_input("FCID（6 碼）", placeholder="例：262174")
with col3:
    debug_to_user = st.toggle("顯示除錯於 UI", value=False)

# ========== 檔案來源選擇 ==========
st.markdown("### 檔案來源")
source = st.radio(
    "選擇來源",
    ["使用者上傳（推薦）", "從 repo 的 data/ 目錄尋找（開發/示範用）"],
    horizontal=True
)

uploaded_zbom = None
uploaded_zcau = None
found = {}

if source == "使用者上傳（推薦）":
    c1, c2 = st.columns(2)
    with c1:
        uploaded_zbom = st.file_uploader("上傳 ZBOM PDF", type=["pdf"])
    with c2:
        if model == "Gamma":
            uploaded_zcau = st.file_uploader("上傳 Zcau Excel", type=["xls", "xlsx"])

else:
    st.info("此模式會到 repo 的 ./data/ 底下尋找檔名包含 FCID 的檔（PDF: 'ZBOM' + 6 碼、Excel: 'zcau' + 6 碼）。")
    data_root = Path("data")
    if st.button("在 data/ 目錄尋找檔案"):
        if not six or not re.fullmatch(r"\d{6}", six.strip()):
            st.warning("請先輸入 6 碼 FCID。")
        else:
            try:
                # 若你要沿用 finder.locate_files，請改寫讓它能在 data_root 運作
                # 這裡示範「直接掃描」的最小法
                zbom_candidates = list(data_root.rglob(f"*ZBOM*{six}*.pdf"))
                zcau_candidates = list(data_root.rglob(f"*zcau*{six}*.xls*"))

                found['machine'] = model
                found['zbom_pdf'] = zbom_candidates[0].as_posix() if zbom_candidates else None
                found['zcau_xls'] = zcau_candidates[0].as_posix() if zcau_candidates else None

                if not found['zbom_pdf'] and not found['zcau_xls']:
                    st.error(f"[{model}] 找不到符合 {six} 的檔案。")
                else:
                    st.success("已在 data/ 找到候選檔。")
                    with st.expander("找到的檔案"):
                        st.write(found)
            except Exception as e:
                st.error(f"尋找時發生未預期錯誤：{e}")

# ========== 觸發判讀 ==========
go = st.button("搜尋 / 判讀")

def show_file_row(label, path_or_buf):
    if path_or_buf is None:
        st.write(f"**{label}**：*(未找到)*")
    else:
        st.write(f"**{label}**：")
        if isinstance(path_or_buf, str):
            st.code(path_or_buf, language="text")
            try:
                with open(path_or_buf, "rb") as f:
                    st.download_button("下載", data=f, file_name=Path(path_or_buf).name, mime=None)
            except Exception:
                pass
        else:
            st.code("(已上傳的檔案)", language="text")
            st.download_button("下載原檔", data=path_or_buf.getbuffer(), file_name=getattr(path_or_buf, "name", "uploaded_file"))

def render_result_block(model_name: str, det: dict):
    st.subheader(f"{model_name} 判讀")
    if not isinstance(det, dict):
        st.write("（無結果或格式錯誤）")
        return
    if model_name == "Vector":
        st.caption("判讀摘要")
        st.write(f"UI Options：{det.get('uiOpt','')}")
        st.write(f"UI Location：{det.get('uiLoc','')}")
        st.write(f"Chase：{det.get('chaseVal','')}")
        st.write(f"BaseType：{det.get('baseType','')}")
    elif model_name == "Gamma":
        st.caption("判讀摘要")
        st.write(f"FOUP Raw：{det.get('foupRaw','')}")
        st.write(f"MPD Raw：{det.get('mpdRaw','')}")
        st.write(f"FOUP Key：{det.get('foupKey','')}")
        st.write(f"UI Key：{det.get('uiKey','')}")
        st.write(f"MPD Key：{det.get('mpdKey','')}")
        st.write(f"BaseType：{det.get('baseType','')}")

    result_text = det.get("result", "") or "（無結果）"
    st.markdown(f"**結果：** <span class='result-pill'>{result_text}</span>", unsafe_allow_html=True)

def render_debug(title: str, det: dict, keys=("debug", "trace")):
    dbg = {}
    meta = det.get("debug_meta") or {}
    for k in keys:
        if isinstance(det.get(k), dict):
            dbg = det[k]
            break
    # 僅在允許時顯示
    can_view = bool(meta.get("can_view")) or (isinstance(dbg, dict) and ("_hint" not in dbg))
    if not can_view:
        return
    with st.expander(title):
        st.json(dbg)

if go:
    # 基本檢查
    if not six or not re.fullmatch(r"\d{6}", six.strip()):
        st.warning("請輸入正確格式：6 位數字（例：262174）。")
        st.stop()

    # 檔案來源處理
    zbom_path = None
    zcau_path = None
    zbom_buf = None
    zcau_buf = None

    if source == "使用者上傳（推薦）":
        if not uploaded_zbom:
            st.error("請上傳 ZBOM PDF。")
            st.stop()
        zbom_buf = uploaded_zbom
        if model == "Gamma" and not uploaded_zcau:
            st.error("[Gamma 判讀] 需同時上傳 ZBOM（PDF）與 BOM（Excel）。")
            st.stop()
        zcau_buf = uploaded_zcau

    else:
        zbom_path = found.get("zbom_pdf")
        zcau_path = found.get("zcau_xls")
        if model == "Vector" and not zbom_path:
            st.error(f"[{model}] 找不到符合 {six} 的 ZBOM 檔案。")
            st.stop()
        if model == "Gamma" and (not zbom_path or not zcau_path):
            st.error("[Gamma 判讀] 需同時找到 PDF 與 BOM（Excel）才能判讀。")
            st.stop()

    # 顯示基本資訊
    st.markdown("### 基本資訊")
    st.write(f"機種：{model}")
    st.write(f"FCID：{six}")

    st.markdown("### 找到的檔案")
    show_file_row("ZBOM PDF", zbom_path or zbom_buf)
    if model == "Gamma":
        show_file_row("Zcau Excel", zcau_path or zcau_buf)

    # 呼叫你原本的判讀函式
    try:
        if model == "Vector":
            # detect_vector 需要實體路徑；若是使用者上傳 buffer，建議你把 detect_vector 改為支援 file-like，
            # 或這裡先把 buffer 暫存到 /tmp 再傳路徑
            if zbom_buf is not None:
                tmp = Path("tmp")
                tmp.mkdir(exist_ok=True)
                tmp_pdf = tmp / f"zbom_{six}.pdf"
                tmp_pdf.write_bytes(zbom_buf.getbuffer())
                zbom_to_use = tmp_pdf.as_posix()
            else:
                zbom_to_use = zbom_path

            det = detect_vector(
                zbom_to_use,
                maps_path=VECTOR_MAP_PATH,
                debug=True,
                debug_to_user=debug_to_user,
                dev_log_path=DEBUG_LOG_PATH
            )
            render_result_block("Vector", det)
            render_debug("除錯（Vector）", det, keys=("debug",))

        elif model == "Gamma":
            # 同上，必要時暫存
            if zbom_buf is not None:
                tmp = Path("tmp"); tmp.mkdir(exist_ok=True)
                tmp_pdf = tmp / f"zbom_{six}.pdf"; tmp_pdf.write_bytes(zbom_buf.getbuffer())
                zbom_to_use = tmp_pdf.as_posix()
            else:
                zbom_to_use = zbom_path

            if zcau_buf is not None:
                tmp = Path("tmp"); tmp.mkdir(exist_ok=True)
                tmp_xls = tmp / f"zcau_{six}.xlsx"; tmp_xls.write_bytes(zcau_buf.getbuffer())
                zcau_to_use = tmp_xls.as_posix()
            else:
                zcau_to_use = zcau_path

            det = detect_gamma(
                zbom_to_use, zcau_to_use,
                maps_path=GAMMA_MAP_PATH,
                debug=True,
                debug_to_user=debug_to_user,
                dev_log_path=DEBUG_LOG_PATH
            )
            render_result_block("Gamma", det)
            render_debug("除錯（Gamma）", det, keys=("debug","trace"))

        else:
            st.info("此機種暫未定義判讀摘要。")

    except Exception as e:
        st.error(f"判讀時發生未預期錯誤：{e}")
