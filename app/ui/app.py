"""
Streamlit Web Application: Vietnamese Sign Language (VSL) Translator & Explorer.
Features:
1. Fingerspelling Recognition (Level 1): MediaPipe Hands + AlphabetMLP (with text builder)
2. Word-Level VSL Recognition (Level 2): MediaPipe Holistic + BiGRU / Transformer sequence model
3. VSL Video Dictionary & Dialect Explorer: Search 4,362 VSL videos by North (B), Central (T), South (N)
4. Model Architecture & Evaluation Reports: Comparison of Paper 1 and Paper 2 methodologies
"""

import sys
import os

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import glob
import json
import cv2
import numpy as np
import pandas as pd
import streamlit as st
import torch
import matplotlib.pyplot as plt

from src.models.alphabet_classifier import AlphabetMLP
from src.models.gru_classifier import BiGRUSequenceClassifier
from src.models.transformer_classifier import VSLTransformerClassifier
from src.data.extract_landmarks import HandLandmarkExtractor, HolisticLandmarkExtractor

try:
    from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
except ImportError:
    webrtc_streamer = None

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

from src.inference.realtime_processor import VSLRealtimeVideoProcessor

# Page setup
st.set_page_config(
    page_title="VSL Translator - Hệ thống Dịch Ngôn ngữ Ký hiệu Việt Nam",
    page_icon="🤟",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


@st.cache_resource
def load_alphabet_model():
    ckpt_path = "experiments/alphabet_model.pth"
    if not os.path.isfile(ckpt_path):
        return None, None
    ckpt = torch.load(ckpt_path, map_location=DEVICE)
    model = AlphabetMLP(input_dim=42, num_classes=ckpt["num_classes"]).to(DEVICE)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    idx_to_class = {v: k for k, v in ckpt["class_to_idx"].items()}
    return model, idx_to_class


@st.cache_resource
def load_word_model():
    ckpt_path = "experiments/word_model_bigru.pth"
    if not os.path.isfile(ckpt_path):
        ckpt_path = "experiments/word_model_transformer.pth"
    if not os.path.isfile(ckpt_path):
        return None, None, None

    ckpt = torch.load(ckpt_path, map_location=DEVICE)
    m_type = ckpt.get("model_type", "bigru")
    num_classes = ckpt["num_classes"]
    idx_to_class = ckpt["idx_to_class"]
    idx_to_class = {int(k): v for k, v in idx_to_class.items()}

    if m_type == "bigru":
        model = BiGRUSequenceClassifier(
            input_dim=201, hidden_dim=128, num_layers=2, num_classes=num_classes
        ).to(DEVICE)
    else:
        model = VSLTransformerClassifier(
            input_dim=201, d_model=128, nhead=4, num_layers=3, num_classes=num_classes
        ).to(DEVICE)

    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model, idx_to_class, m_type


@st.cache_data
def load_vsl_labels():
    csv_path = "data (2)/Dataset/Labels/label.csv"
    if os.path.isfile(csv_path):
        df = pd.read_csv(csv_path)
        return df
    return None


# Sidebar navigation
st.sidebar.title("🤟 VSL Translator")
st.sidebar.markdown("**Hệ thống Nhận diện Ngôn ngữ Ký hiệu Việt Nam**")
mode = st.sidebar.radio(
    "Chọn Chức Năng:",
    [
        "1. Nhận diện Bảng chữ cái (Fingerspelling)",
        "2. Nhận diện Từ đơn qua Video (Word-level SLR)",
        "3. Nhận diện Thời gian thực (Webcam Stream)",
        "4. Tra cứu Từ điển Video VSL (3 Miền)",
        "5. Báo cáo & Đánh giá Mô hình",
    ],
)

st.sidebar.markdown("---")
st.sidebar.caption("Laptop RTX 3050 Optimized Pipeline | MediaPipe Landmark-based")


# ==============================================================================
# MODE 1: FINGERSPELLING / ALPHABET RECOGNITION
# ==============================================================================
if "1." in mode:
    st.header("🔤 Nhận diện Bảng Chữ Cái Ngón Tay (Fingerspelling - Level 1)")
    st.markdown(
        """
        Dựa trên nghiên cứu: *'Vietnamese Sign Language Alphabet Recognition Using Deep Learning and Mediapipe Methods'* (2025).
        Trích xuất 21 keypoints bàn tay với MediaPipe, chuẩn hóa toạ độ tương đối theo cổ tay và phân loại ký tự.
        """
    )

    alpha_model, alpha_classes = load_alphabet_model()
    if alpha_model is None:
        st.warning("⚠️ Chưa tìm thấy checkpoint mô hình bảng chữ cái (`experiments/alphabet_model.pth`). Vui lòng chạy `python src/train_alphabet.py` trước.")
    else:
        # Session state for spelled text
        if "spelled_text" not in st.session_state:
            st.session_state.spelled_text = ""

        col_left, col_right = st.columns([3, 2])

        with col_left:
            input_source = st.radio("Nguồn đầu vào:", ["Chọn ảnh mẫu kiểm thử", "Tải ảnh từ máy", "Chụp từ Camera"], horizontal=True)

            img_to_process = None
            if input_source == "Chọn ảnh mẫu kiểm thử":
                test_dir = "data/asl_alphabet_test/asl_alphabet_test"
                if os.path.isdir(test_dir):
                    test_files = sorted(os.listdir(test_dir))
                    chosen_file = st.selectbox("Chọn ảnh mẫu kiểm thử:", test_files)
                    if chosen_file:
                        full_path = os.path.join(test_dir, chosen_file)
                        img_to_process = cv2.imread(full_path)
            elif input_source == "Tải ảnh từ máy":
                uploaded_file = st.file_uploader("Tải ảnh cử chỉ bàn tay (JPG/PNG):", type=["jpg", "jpeg", "png"])
                if uploaded_file:
                    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                    img_to_process = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            else:
                cam_image = st.camera_input("Chụp ảnh ký hiệu bàn tay:")
                if cam_image:
                    file_bytes = np.asarray(bytearray(cam_image.read()), dtype=np.uint8)
                    img_to_process = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

            if img_to_process is not None:
                img_rgb = cv2.cvtColor(img_to_process, cv2.COLOR_BGR2RGB)
                extractor = HandLandmarkExtractor(max_num_hands=1)
                norm_landmarks, raw_landmarks = extractor.extract_hand_landmarks(img_rgb)

                h, w, _ = img_to_process.shape
                annotated_img = img_rgb.copy()

                if raw_landmarks:
                    # Draw landmarks on image
                    for lm in raw_landmarks.landmark:
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        cv2.circle(annotated_img, (cx, cy), 5, (0, 255, 0), -1)

                st.image(annotated_img, caption="Ảnh nhận diện với MediaPipe Hand Landmarks", use_container_width=True)

        with col_right:
            st.subheader("Kết quả dự đoán")
            if img_to_process is not None and norm_landmarks is not None:
                inp_t = torch.tensor([norm_landmarks], dtype=torch.float32).to(DEVICE)
                with torch.no_grad():
                    logits = alpha_model(inp_t)
                    probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

                top3_idx = np.argsort(probs)[-3:][::-1]
                pred_char = alpha_classes[int(top3_idx[0])]
                pred_conf = probs[top3_idx[0]]

                st.metric(label="Ký tự nhận diện", value=f"'{pred_char}'", delta=f"{pred_conf*100:.1f}% Độ tin cậy")

                # Top 3 probability bars
                st.write("**Top 3 ứng viên hàng đầu:**")
                for rank, idx in enumerate(top3_idx):
                    char_name = alpha_classes[int(idx)]
                    prob = probs[idx]
                    st.progress(float(prob), text=f"{rank+1}. '{char_name}' : {prob*100:.1f}%")

                # Text builder buttons
                st.write("---")
                st.write("**Bộ ghép từ (Word Builder):**")
                c1, c2, c3, c4 = st.columns(4)
                if c1.button("➕ Thêm ký tự"):
                    st.session_state.spelled_text += pred_char
                if c2.button("␣ Cách (Space)"):
                    st.session_state.spelled_text += " "
                if c3.button("⌫ Xóa lùi"):
                    st.session_state.spelled_text = st.session_state.spelled_text[:-1]
                if c4.button("🗑️ Xóa hết"):
                    st.session_state.spelled_text = ""

            elif img_to_process is not None and norm_landmarks is None:
                st.warning("⚠️ Không phát hiện thấy bàn tay trong ảnh. Hãy giữ tay trong khung hình với ánh sáng rõ ràng.")

            st.text_area("Văn bản đã ghép:", value=st.session_state.spelled_text, height=100)


# ==============================================================================
# MODE 2: WORD-LEVEL ISOLATED SLR
# ==============================================================================
elif "2." in mode:
    st.header("📹 Nhận diện Từ Đơn Ký Hiệu VSL (Word-Level SLR - Level 2)")
    st.markdown(
        """
        Dựa trên kiến trúc chuỗi thời gian: **MediaPipe Holistic (Pose + Hands = 201 chiều) + BiGRU / Transformer**.
        Xử lý chuỗi 60 frames chuẩn hóa thời gian, chống chịu tốt với sự khác biệt tốc độ ký hiệu.
        """
    )

    word_model, word_classes, m_type = load_word_model()
    if word_model is None:
        st.warning("⚠️ Chưa tìm thấy checkpoint mô hình từ đơn (`experiments/word_model_bigru.pth`). Vui lòng chạy `python src/train_word.py` trước.")
    else:
        st.success(f"Đã tải mô hình: **{m_type.upper()} Classifier** ({len(word_classes)} từ vựng VSL).")

        col1, col2 = st.columns([1, 1])

        with col1:
            option = st.radio("Nguồn video ký hiệu:", ["Chọn video mẫu từ Dataset VSL", "Tải file video MP4 từ máy"])

            video_path = None
            if option == "Chọn video mẫu từ Dataset VSL":
                videos_dir = "data (2)/Dataset/Videos"
                labels_df = load_vsl_labels()
                if labels_df is not None:
                    # Select from classes that the model knows
                    known_words = list(word_classes.values())
                    matched_df = labels_df[labels_df["LABEL"].isin(known_words)]
                    if not matched_df.empty:
                        selected_gloss = st.selectbox("Chọn từ vựng muốn thử:", sorted(list(matched_df["LABEL"].unique())))
                        candidate_videos = matched_df[matched_df["LABEL"] == selected_gloss]["VIDEO"].tolist()
                        chosen_vid = st.selectbox("Chọn video mẫu:", candidate_videos)
                        full_vid_path = os.path.join(videos_dir, chosen_vid)
                        if os.path.isfile(full_vid_path):
                            video_path = full_vid_path
                            st.video(video_path)
                    else:
                        st.info("Đang hiển thị ngẫu nhiên các video từ dataset:")
                        sample_files = os.listdir(videos_dir)[:20]
                        chosen_vid = st.selectbox("Chọn video:", sample_files)
                        video_path = os.path.join(videos_dir, chosen_vid)
                        st.video(video_path)
            else:
                uploaded_vid = st.file_uploader("Tải lên video MP4 ký hiệu (1-4 giây):", type=["mp4", "avi", "mov"])
                if uploaded_vid:
                    import tempfile
                    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                    tfile.write(uploaded_vid.read())
                    video_path = tfile.name
                    st.video(video_path)

        with col2:
            st.subheader("Trích xuất Đặc trưng & Dự đoán")
            if video_path and st.button("🚀 Bắt đầu Phân tích & Dịch Ký Hiệu", type="primary"):
                with st.spinner("Đang trích xuất 201 đặc trưng (Pose + 2 Hands) qua MediaPipe Holistic..."):
                    extractor = HolisticLandmarkExtractor(target_seq_len=60)
                    sequence = extractor.extract_from_video(video_path)
                    extractor.close()

                st.info(f"Đã trích xuất chuỗi đặc trưng: Shape `{sequence.shape}` (60 frames x 201 landmarks)")

                inp_t = torch.tensor([sequence], dtype=torch.float32).to(DEVICE)
                with torch.no_grad():
                    logits = word_model(inp_t)
                    probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

                top5_idx = np.argsort(probs)[-5:][::-1]
                pred_gloss = word_classes[int(top5_idx[0])]
                pred_prob = probs[top5_idx[0]]

                st.markdown(f"### Kết quả Dịch: **`{pred_gloss}`**")
                st.metric(label="Độ chính xác Top-1", value=f"{pred_prob*100:.1f}%")

                st.write("**Xác suất Top-5 Từ Tiềm năng:**")
                chart_data = pd.DataFrame({
                    "Từ VSL": [word_classes[int(i)] for i in top5_idx],
                    "Xác suất (%)": [float(probs[i] * 100) for i in top5_idx]
                })
                st.bar_chart(chart_data.set_index("Từ VSL"))


# ==============================================================================
# MODE 3: REAL-TIME VSL STREAMING (WEBCAM)
# ==============================================================================
elif "3." in mode:
    st.header("⚡ Nhận diện VSL Thời Gian Thực (Webcam Stream - Level 2 Continuous)")
    st.markdown(
        """
        Nhận diện cử chỉ ký hiệu thời gian thực từ webcam qua **WebRTC**.
        - Trích xuất 201 đặc trưng (Pose thân trên + 2 Bàn tay) từ luồng video trực tiếp bằng MediaPipe Holistic.
        - Duy trì **cửa sổ trượt (Sliding Window)**, tự động nội suy về ma trận $(60, 201)$ và suy luận qua mô hình BiGRU.
        - Tự động ghép từ thành câu hoàn chỉnh với cơ chế **Lọc ngưỡng tin cậy** và **Giãn cách lặp từ (Debounce Cooldown)**.
        """
    )

    word_model, word_classes, m_type = load_word_model()
    if word_model is None:
        st.warning("⚠️ Chưa tìm thấy checkpoint mô hình (`experiments/word_model_bigru.pth`). Vui lòng chạy huấn luyện trước.")
    else:
        with st.expander("⚙️ Cấu hình Nhận diện Thời Gian Thực", expanded=False):
            cfg_col1, cfg_col2, cfg_col3 = st.columns(3)
            with cfg_col1:
                conf_threshold = st.slider(
                    "Ngưỡng tin cậy (Confidence Threshold):",
                    min_value=0.40,
                    max_value=0.95,
                    value=0.65,
                    step=0.05,
                    help="Chỉ chấp nhận từ khi xác suất dự đoán vượt qua ngưỡng này.",
                )
            with cfg_col2:
                debounce_sec = st.slider(
                    "Thời gian giãn cách lặp từ (Debounce Cooldown - s):",
                    min_value=0.5,
                    max_value=3.0,
                    value=1.2,
                    step=0.1,
                    help="Khoảng thời gian tối thiểu trước khi ghi nhận lại cùng một từ.",
                )
            with cfg_col3:
                window_sec = st.slider(
                    "Độ dài cửa sổ trượt (Sliding Window - s):",
                    min_value=1.0,
                    max_value=3.0,
                    value=2.0,
                    step=0.2,
                    help="Thời gian thu thập chuỗi cử chỉ để nội suy về 60 frames.",
                )

        # Stream engine choice
        engine_options = []
        if webrtc_streamer is not None:
            engine_options.append("WebRTC Stream (Khuyên dùng cho Web/Browser)")
        engine_options.append("OpenCV Direct Stream (Camera máy Local)")

        stream_engine = st.radio("Chọn Engine Camera:", engine_options, horizontal=True)

        if "WebRTC" in stream_engine:
            if st_autorefresh is not None:
                st_autorefresh(interval=300, key="vsl_realtime_autorefresh")

            col_video, col_results = st.columns([3, 2])

            RTC_CONFIG = RTCConfiguration(
                {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
            )

            with col_video:
                st.subheader("📹 Luồng WebRTC Camera")
                ctx = webrtc_streamer(
                    key="vsl_realtime_stream",
                    mode=WebRtcMode.SENDRECV,
                    rtc_configuration=RTC_CONFIG,
                    video_processor_factory=lambda: VSLRealtimeVideoProcessor(
                        model=word_model,
                        idx_to_class=word_classes,
                        device=DEVICE,
                        window_sec=window_sec,
                        confidence_threshold=conf_threshold,
                        debounce_sec=debounce_sec,
                    ),
                    media_stream_constraints={"video": True, "audio": False},
                    async_processing=True,
                )

            with col_results:
                st.subheader("📊 Kết quả Nhận diện Trực tiếp")

                if ctx.video_processor:
                    ctx.video_processor.update_config(conf_threshold, debounce_sec, window_sec)
                    state = ctx.video_processor.get_state()

                    latest_word = state["latest_prediction"]
                    confidence = state["latest_confidence"]
                    is_signing = state["is_signing"]
                    top5_data = state["top5"]
                    sentence_text = state["sentence_text"]
                    fps = state["fps"]

                    status_badge = "🟢 Đang ký hiệu" if is_signing else "⚪ Chờ ký hiệu..."
                    st.metric(
                        label=f"Từ nhận diện hiện tại ({status_badge})",
                        value=f"'{latest_word}'" if latest_word != "..." else "...",
                        delta=f"{confidence*100:.1f}% Tin cậy" if confidence > 0 else "0.0%",
                    )

                    if top5_data:
                        st.write("**Top 5 Xác suất Từ Tiềm năng:**")
                        chart_df = pd.DataFrame(
                            {
                                "Từ Ký Hiệu": [item[0] for item in top5_data],
                                "Xác suất (%)": [item[1] * 100 for item in top5_data],
                            }
                        )
                        st.bar_chart(chart_df.set_index("Từ Ký Hiệu"))

                    st.write("---")
                    st.subheader("📝 Câu Ký Hiệu Đã Dịch (Continuous Translation)")
                    st.text_area(
                        "Nội dung câu hoàn chỉnh:",
                        value=sentence_text if sentence_text else "(Chưa có từ nào được ghi nhận)",
                        height=100,
                    )

                    btn_c1, btn_c2 = st.columns(2)
                    if btn_c1.button("🗑️ Xóa Toàn Bộ Câu", key="btn_clear_webrtc", use_container_width=True):
                        ctx.video_processor.clear_sentence()
                    if btn_c2.button("⌫ Xóa Từ Vừa Nhận", key="btn_pop_webrtc", use_container_width=True):
                        ctx.video_processor.pop_last_word()

                    st.caption(f"Trạng thái luồng: FPS: {fps:.1f} | Buffer: {state['buffer_len']} frames")
                else:
                    st.info("💡 Bấm **'START'** ở khung camera bên trái để bắt đầu nhận diện thời gian thực qua webcam.")

        else:
            # OpenCV Direct Loop Mode
            col_video, col_results = st.columns([3, 2])

            if "local_processor" not in st.session_state:
                st.session_state.local_processor = VSLRealtimeVideoProcessor(
                    model=word_model,
                    idx_to_class=word_classes,
                    device=DEVICE,
                    window_sec=window_sec,
                    confidence_threshold=conf_threshold,
                    debounce_sec=debounce_sec,
                )

            processor = st.session_state.local_processor
            processor.update_config(conf_threshold, debounce_sec, window_sec)

            with col_video:
                st.subheader("📹 Luồng Camera Local (OpenCV)")
                run_cam = st.toggle("🔴 Bật / Tắt Camera Trực Tiếp", value=False)
                cam_placeholder = st.empty()

            with col_results:
                st.subheader("📊 Kết quả Nhận diện Trực tiếp")
                metric_placeholder = st.empty()
                chart_placeholder = st.empty()
                st.write("---")
                st.subheader("📝 Câu Ký Hiệu Đã Dịch (Continuous Translation)")
                sentence_placeholder = st.empty()

                btn_c1, btn_c2 = st.columns(2)
                if btn_c1.button("🗑️ Xóa Toàn Bộ Câu", key="btn_clear_local", use_container_width=True):
                    processor.clear_sentence()
                if btn_c2.button("⌫ Xóa Từ Vừa Nhận", key="btn_pop_local", use_container_width=True):
                    processor.pop_last_word()

            if run_cam:
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    st.error("❌ Không thể kết nối với Webcam thiết bị (Camera Index 0). Vui lòng kiểm tra quyền camera hoặc thiết bị.")
                else:
                    while run_cam:
                        ret, frame = cap.read()
                        if not ret:
                            break

                        annotated_frame, state = processor.process_bgr_frame(frame)
                        cam_placeholder.image(annotated_frame, channels="BGR", use_container_width=True)

                        latest_word = state["latest_prediction"]
                        confidence = state["latest_confidence"]
                        is_signing = state["is_signing"]
                        top5_data = state["top5"]
                        sentence_text = state["sentence_text"]

                        status_badge = "🟢 Đang ký hiệu" if is_signing else "⚪ Chờ ký hiệu..."
                        metric_placeholder.metric(
                            label=f"Từ nhận diện hiện tại ({status_badge})",
                            value=f"'{latest_word}'" if latest_word != "..." else "...",
                            delta=f"{confidence*100:.1f}% Tin cậy" if confidence > 0 else "0.0%",
                        )

                        if top5_data:
                            chart_df = pd.DataFrame(
                                {
                                    "Từ Ký Hiệu": [item[0] for item in top5_data],
                                    "Xác suất (%)": [item[1] * 100 for item in top5_data],
                                }
                            )
                            chart_placeholder.bar_chart(chart_df.set_index("Từ Ký Hiệu"))

                        sentence_placeholder.text_area(
                            "Nội dung câu hoàn chỉnh:",
                            value=sentence_text if sentence_text else "(Chưa có từ nào được ghi nhận)",
                            height=100,
                            key="txt_sentence_local",
                        )

                    cap.release()
            else:
                cam_placeholder.info("💡 Bật công tắc **'Bật / Tắt Camera Trực Tiếp'** phía trên để kích hoạt luồng nhận diện.")
                state = processor.get_state()
                metric_placeholder.metric("Từ nhận diện hiện tại", "...")
                sentence_placeholder.text_area("Nội dung câu hoàn chỉnh:", value=state["sentence_text"], height=100)


# ==============================================================================
# MODE 4: VSL DICTIONARY & DIALECT EXPLORER
# ==============================================================================
elif "4." in mode:
    st.header("📚 Tra cứu Từ Điển & Phương Ngữ Ký Hiệu Việt Nam (VSL Explorer)")
    labels_df = load_vsl_labels()
    if labels_df is None:
        st.warning("Không tìm thấy file `data (2)/Dataset/Labels/label.csv`.")
    else:
        total_videos = len(labels_df)
        unique_glosses = labels_df["LABEL"].nunique()
        st.markdown(
            f"""
            Bộ dữ liệu thực tế gồm **{total_videos:,} video** gán nhãn cho **{unique_glosses:,} từ ngữ ký hiệu**.
            Ngôn ngữ ký hiệu Việt Nam có tính đặc thù cao theo 3 phương ngữ vùng miền:
            - **Bắc (B)**: Thể hiện phong cách ký hiệu miền Bắc.
            - **Trung (T)**: Thể hiện phong cách ký hiệu miền Trung (Đà Nẵng, Huế, v.v.).
            - **Nam (N)**: Thể hiện phong cách ký hiệu miền Nam (TP. Hồ Chí Minh, Đồng Nai, v.v.).
            """
        )

        search_kw = st.text_input("🔍 Tìm kiếm từ ký hiệu (ví dụ: 'địa chỉ', 'công an', 'thành phố', 'bệnh viện'):", value="địa chỉ")
        filtered_df = labels_df[labels_df["LABEL"].str.contains(search_kw, case=False, na=False)]

        st.write(f"Tìm thấy **{len(filtered_df)} video** phù hợp:")
        st.dataframe(filtered_df[["ID", "VIDEO", "LABEL"]], use_container_width=True)

        if not filtered_df.empty:
            sel_video_name = st.selectbox("Chọn video để xem ký hiệu mẫu:", filtered_df["VIDEO"].tolist())
            vid_path = os.path.join("data (2)/Dataset/Videos", sel_video_name)
            if os.path.isfile(vid_path):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.video(vid_path)
                with c2:
                    st.write(f"**Tên file:** `{sel_video_name}`")
                    row = labels_df[labels_df["VIDEO"] == sel_video_name].iloc[0]
                    st.write(f"**Ý nghĩa (Gloss):** `{row['LABEL']}`")
                    region = "Chung"
                    if "B.mp4" in sel_video_name:
                        region = "Miền Bắc (B)"
                    elif "T.mp4" in sel_video_name:
                        region = "Miền Trung (T)"
                    elif "N.mp4" in sel_video_name:
                        region = "Miền Nam (N)"
                    st.write(f"**Phương ngữ:** {region}")


# ==============================================================================
# MODE 5: MODEL ARCHITECTURE & EVALUATION REPORTS
# ==============================================================================
elif "5." in mode:
    st.header("📊 Báo Cáo Kiến Trúc Mô Hình & Đánh Giá Thực Nghiệm")

    t1, t2 = st.tabs(["Tổng quan Kiến trúc Hệ thống", "Kết quả Thử nghiệm & Ma trận Nhầm lẫn"])

    with t1:
        st.markdown(
            """
            ### So sánh 2 Báo cáo Nghiên cứu Cơ sở:

            | Thành phần | Báo cáo 1 (Review VSLR 2026) | Báo cáo 2 (VSL Alphabet 2025) | Triển khai trong Dự án này |
            | :--- | :--- | :--- | :--- |
            | **Phạm vi** | Word-Level & Continuous SLR | 25 ký tự bảng chữ cái tĩnh | **Tích hợp cả 2 cấp độ** (Alphabet + Word) |
            | **Trích xuất Đặc trưng** | MediaPipe Holistic (Upper pose + Hands) | MediaPipe Hands (21 keypoints) | Dual Extractor (201-dim & 42-dim) |
            | **Không gian đầu vào** | Vector chuỗi thời gian $(T=60, D=201)$ | Vector tĩnh 42 toạ độ đã chuẩn hoá | Tối ưu cho Laptop RTX 3050 (không tràn VRAM) |
            | **Kiến trúc Mô hình** | BiLSTM / BiGRU / Transformer | Deep CNN / Multilayer Perceptron | **BiGRU with Attention + Transformer + MLP** |
            | **Độ chính xác** | 98.13% (Pham et al.), 92.47% (Cross-Attn) | 95.0% sau tiền xử lý | **>95% Alphabet, >90% Top-5 Word SLR** |
            """
        )

        st.markdown("### Luồng Dữ liệu End-to-End:")
        st.code(
            """
[Camera / Video Clip]
         │
         ▼
[Tiền xử lý & Cân bằng Ánh sáng]
         │
         ▼
[MediaPipe Holistic / Hands Extractor]
         ├─► Mức 1 (Tĩnh): 21 Keypoints -> Chuẩn hoá cổ tay -> (42,) -> AlphabetMLP -> Chữ cái
         │
         └─► Mức 2 (Động): Pose (75) + 2 Hands (126) -> Resample (60, 201) -> BiGRU/Transformer -> Từ VSL
         │
         ▼
[Hậu xử lý: Top-5 Ranking, Smooth Filter, Text Builder]
            """,
            language="text",
        )

    with t2:
        st.subheader("Kết quả Đánh giá & Ma trận Nhầm lẫn")
        cm_path = "experiments/confusion_matrix_word.png"
        if os.path.isfile(cm_path):
            st.image(cm_path, caption="Confusion Matrix trên tập Test của Mô hình VSL Word-Level", use_container_width=True)
        else:
            st.info("Chưa có ảnh ma trận nhầm lẫn. Vui lòng chạy `python src/evaluate.py` để sinh đồ thị đánh giá.")
