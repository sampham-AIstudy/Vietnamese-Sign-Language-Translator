"""
VSL Core Translation CLI Runner (Công cụ Kiểm thử & Thực thi Lõi Độc lập)

Cho phép chạy và kiểm thử trực tiếp Pipeline Lõi VSL qua dòng lệnh PowerShell / Terminal:
1. Chế độ đơn lẻ: python run_core.py --gloss "TÔI BÁC SĨ KHÁM BỆNH"
2. Chế độ hàng loạt: python run_core.py --benchmark
3. Chế độ tương tác REPL: python run_core.py --interactive
4. Chế độ nhận diện liên tục từ tệp keypoints: python run_core.py --keypoints <path_to_npz>
"""

import sys
import argparse
import time
from pathlib import Path

# Thiết lập encoding UTF-8 cho console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.translation.end_to_end import VSLEndToEndTranslator


BENCHMARK_SAMPLES = [
    ["BẠN", "TÊN", "GÌ"],
    ["TÔI", "HỌC", "SINH"],
    ["BÂY GIỜ", "MẤY", "GIỜ"],
    ["TÔI", "MUỐN", "UỐNG", "NƯỚC"],
    ["HÔM NAY", "TRỜI", "MƯA", "TO"],
    ["BẠN", "SỐNG", "Ở", "ĐÂU"],
    ["CẢM ƠN", "BẠN", "RẤT", "NHIỀU"],
    ["TÔI", "BÁC SĨ", "BỆNH VIỆN", "LÀM VIỆC"],
]


def print_banner():
    print("=" * 70)
    print("  VIETNAMESE SIGN LANGUAGE TRANSLATOR (VSLT) - CORE PIPELINE ENGINE")
    print("  Mô hình CSLR (ST-GCN + BiGRU) + ViT5 Seq2Seq + Lexicon Bank 8 Phương ngữ")
    print("=" * 70)


def run_benchmark(engine: VSLEndToEndTranslator):
    print("\n--- BẮT ĐẦU CHẠY BENCHMARK DỊCH THUẬT LÕI (8 MẪU KÝ HIỆU TIÊU CHUẨN) ---")
    total_time = 0.0

    for idx, sample in enumerate(BENCHMARK_SAMPLES, 1):
        res = engine.translate_glosses(sample, attach_lexicon=True)
        total_time += res["latency_ms"]
        print(f"\n[Mẫu {idx}]")
        print(f"  - Ký hiệu đầu vào: {' '.join(sample)}")
        print(f"  - Dịch tiếng Việt: \033[92m{res['translation']}\033[0m")
        print(f"  - Độ trễ suy luận: {res['latency_ms']} ms")
        
        matches = res.get("lexicon_matches", {})
        if matches:
            match_str = ", ".join([f"{k} ({len(v)} video)" for k, v in matches.items()])
            print(f"  - Video đối sánh từ điển: {match_str}")

    avg_time = total_time / len(BENCHMARK_SAMPLES)
    print("\n" + "-" * 70)
    print(f"KẾT QUẢ BENCHMARK: Hoàn tất 8/8 mẫu | Thời gian trung bình: {avg_time:.2f} ms/câu")
    print("-" * 70)


def run_interactive(engine: VSLEndToEndTranslator):
    print("\n--- BẮT ĐẦU CHẾ ĐỘ TƯƠNG TÁC DÒNG LỆNH (Gõ 'exit' hoặc 'quit' để thoát) ---")
    print("Nhập chuỗi ký hiệu VSL (ví dụ: 'tôi muốn uống nước' hoặc 'BẠN ĐI ĐÂU'):\n")

    while True:
        try:
            line = input("VSL-Gloss > ").strip()
            if not line:
                continue
            if line.lower() in ["exit", "quit", "q"]:
                print("Đã thoát chế độ tương tác.")
                break

            res = engine.translate_glosses(line, attach_lexicon=True)
            print(f"  ==> Tiếng Việt: \033[92m{res['translation']}\033[0m  ({res['latency_ms']} ms)")
            
            matches = res.get("lexicon_matches", {})
            if matches:
                for word, vids in matches.items():
                    sample_vid = vids[0]
                    print(f"      [Từ điển: {word}] -> {sample_vid.get('video_filename')} ({sample_vid.get('region')})")
            print()

        except KeyboardInterrupt:
            print("\nĐã hủy tương tác.")
            break
        except Exception as e:
            print(f"  [LỖI]: {e}")


def main():
    parser = argparse.ArgumentParser(description="VSL Core Translation CLI Runner")
    parser.add_argument("--gloss", type=str, default=None, help="Chuỗi ký hiệu cần dịch (vd: 'TÔI ĐI HỌC')")
    parser.add_argument("--benchmark", action="store_true", help="Chạy bộ benchmark kiểm thử tiêu chuẩn")
    parser.add_argument("--interactive", "-i", action="store_true", help="Mở chế độ REPL tương tác trực tiếp")
    parser.add_argument("--webcam", type=int, default=None, help="Bật Webcam quét cử chỉ tay trực tiếp (ví dụ: --webcam 0)")
    parser.add_argument("--video", type=str, default=None, help="Đường dẫn file video mp4 cần quét cử chỉ")
    parser.add_argument("--keypoints", type=str, default=None, help="Đường dẫn tệp .npy/.npz chứa tọa độ keypoints")
    parser.add_argument("--device", type=str, default=None, help="Thiết bị suy luận ('cuda' hoặc 'cpu')")
    args = parser.parse_args()

    print_banner()

    # Xử lý chế độ Webcam hoặc Video File trực tiếp
    if args.webcam is not None:
        from realtime_demo import RealtimeDemo
        print(f"\n[KHỞI CHẠY WEBCAM] Mở thiết bị Camera Index: {args.webcam}...")
        demo = RealtimeDemo(source=str(args.webcam))
        demo.run()
        return
    elif args.video:
        from realtime_demo import RealtimeDemo
        print(f"\n[KHỞI CHẠY VIDEO] Đọc cử chỉ từ video: {args.video}...")
        demo = RealtimeDemo(source=args.video)
        demo.run()
        return

    print("Đang khởi tạo Engine Lõi...")
    engine = VSLEndToEndTranslator(device=args.device)
    info = engine.get_info()
    print(f"  - Thiết bị: {info['device']}")
    print(f"  - ViT5 Model: {info['translator']['architecture']} ({info['translator']['total_parameters']:,} params)")
    print(f"  - CSLR Model: {'Sẵn sàng' if info['cslr_enabled'] else 'Không khả dụng'}")
    print(f"  - Lexicon Bank: {info.get('lexicon_entries', 0)} video ({len(info.get('lexicon_regions', []))} phương ngữ)")
    print(f"  - Thời gian nạp: {info['init_duration_s']} giây")

    if args.benchmark:
        run_benchmark(engine)
    elif args.gloss:
        res = engine.translate_glosses(args.gloss, attach_lexicon=True)
        print("\nKẾT QUẢ DỊCH:")
        print(f"  - Đầu vào: {res['source_raw']}")
        print(f"  - Câu dịch tiếng Việt: \033[92m{res['translation']}\033[0m")
        print(f"  - Độ trễ: {res['latency_ms']} ms")
        matches = res.get("lexicon_matches", {})
        if matches:
            print("  - Video ký hiệu đối sánh:")
            for k, v in matches.items():
                print(f"    + '{k}': {len(v)} video đối chiếu (vùng: {v[0].get('region')})")
    elif args.keypoints:
        import numpy as np
        kp_file = Path(args.keypoints)
        if not kp_file.exists():
            print(f"[LỖI]: Không tìm thấy tệp {kp_file}")
            return
        loaded = np.load(str(kp_file))
        if isinstance(loaded, np.ndarray):
            kps = loaded
            masks = None
        else:
            kps = loaded["keypoints"] if "keypoints" in loaded else loaded["arr_0"]
            masks = loaded.get("visibility_mask", None)
        print(f"\nĐang suy luận từ khung xương ({kps.shape[0]} frames)...")
        res = engine.translate_keypoints(kps, joint_mask=masks)
        print("\nKẾT QUẢ DỊCH KHUNG XƯƠNG CSLR -> ViT5:")
        print(f"  - CSLR Glosses dự đoán: {res['predicted_gloss_str']}")
        print(f"  - Câu dịch tiếng Việt: \033[92m{res['translation']}\033[0m")
        print(f"  - Độ trễ CSLR: {res['cslr_latency_ms']} ms | ViT5: {res['vit5_latency_ms']} ms | Tổng: {res['total_latency_ms']} ms")
    else:
        # Default to interactive REPL
        run_interactive(engine)


if __name__ == "__main__":
    main()
