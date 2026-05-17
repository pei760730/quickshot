#!/usr/bin/env python3
"""
影音轉逐字稿工具

用法：
  python scripts/utils/transcribe.py "https://drive.google.com/file/d/xxx/view"
  python scripts/utils/transcribe.py /path/to/video.mp4
  python scripts/utils/transcribe.py /path/to/audio.m4a
  python scripts/utils/transcribe.py /path/to/file --model medium

支援格式：
  影片：.mp4 .mov .avi .mkv .webm
  音檔：.m4a .mp3 .wav .ogg .flac .aac
輸出：帶時間戳的逐字稿（純文字）
依賴：ffmpeg + faster-whisper（由 session-start.sh 自動安裝）
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".ogg", ".flac", ".aac"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def is_audio_file(path):
    """判斷是否為音檔（非影片）"""
    return Path(path).suffix.lower() in AUDIO_EXTENSIONS


def convert_audio(input_path, output_path):
    """用 ffmpeg 將音檔轉為 16kHz mono WAV（whisper 最佳格式）"""
    subprocess.run([
        "ffmpeg", "-i", input_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        output_path, "-y"
    ], capture_output=True, check=True)


def gdrive_to_direct_url(url):
    """Google Drive 共享連結 → 直接下載 URL"""
    # https://drive.google.com/file/d/FILE_ID/view?usp=sharing
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url


def download_video(url, output_path):
    """下載影片到本機"""
    direct_url = gdrive_to_direct_url(url)
    subprocess.run(
        ["curl", "-L", "-o", output_path, "-s", direct_url],
        check=True
    )
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"下載失敗：{url}")


def extract_audio(video_path, audio_path):
    """用 ffmpeg 從影片抽出音訊（16kHz mono WAV）"""
    subprocess.run([
        "ffmpeg", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        audio_path, "-y"
    ], capture_output=True, check=True)


def transcribe(audio_path, model_size="medium"):
    """用 faster-whisper 轉逐字稿"""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("❌ faster-whisper 未安裝。請執行：pip install faster-whisper")
        sys.exit(1)

    model = WhisperModel(model_size, compute_type="int8")
    segments, info = model.transcribe(audio_path, language="zh")

    results = []
    for seg in segments:
        results.append({
            "start": round(seg.start, 1),
            "end": round(seg.end, 1),
            "text": seg.text.strip()
        })
    return results, info


def main():
    if len(sys.argv) < 2:
        print("用法：python scripts/utils/transcribe.py <影片或音檔路徑/Google Drive連結> [--model medium]")
        sys.exit(1)

    source = sys.argv[1]
    model_size = "medium"

    # 解析 --model 參數
    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        if idx + 1 < len(sys.argv):
            model_size = sys.argv[idx + 1]

    # 建立暫存目錄
    tmp_dir = tempfile.mkdtemp(prefix="transcribe_")
    video_path = os.path.join(tmp_dir, "video.mp4")
    audio_path = os.path.join(tmp_dir, "audio.wav")

    try:
        # Step 1：取得來源
        if source.startswith("http"):
            print(f"📥 下載中：{source[:60]}...")
            download_video(source, video_path)
            print("✅ 下載完成")
            # Step 2：從影片抽音訊
            print("🔊 抽取音訊...")
            extract_audio(video_path, audio_path)
            print("✅ 音訊抽取完成")
        elif is_audio_file(source):
            # 音檔：直接轉 WAV，跳過影片抽取
            if not os.path.exists(source):
                print(f"❌ 檔案不存在：{source}")
                sys.exit(1)
            ext = Path(source).suffix.lower()
            if ext == ".wav":
                audio_path = source
                print("🔊 WAV 音檔，直接使用")
            else:
                print(f"🔊 轉換音檔（{ext}→wav）...")
                convert_audio(source, audio_path)
                print("✅ 音檔轉換完成")
        else:
            # 影片檔
            video_path = source
            if not os.path.exists(video_path):
                print(f"❌ 檔案不存在：{video_path}")
                sys.exit(1)
            # Step 2：從影片抽音訊
            print("🔊 抽取音訊...")
            extract_audio(video_path, audio_path)
            print("✅ 音訊抽取完成")

        # Step 3：轉逐字稿
        print(f"📝 轉寫中（模型：{model_size}）...")
        segments, info = transcribe(audio_path, model_size)
        print(f"✅ 轉寫完成｜語言：{info.language}｜片長：{info.duration:.1f}秒")

        # 輸出帶時間戳版本
        print("\n--- 逐字稿（帶時間戳）---\n")
        for seg in segments:
            print(f"[{seg['start']:.1f}s → {seg['end']:.1f}s] 「{seg['text']}」")

        # 輸出純文字版本
        print("\n--- 純文字 ---\n")
        print("\n".join(seg["text"] for seg in segments))

    finally:
        # 清理暫存檔（不刪使用者的原始檔案）
        tmp = Path(tmp_dir)
        for f in tmp.iterdir():
            f.unlink(missing_ok=True)
        tmp.rmdir() if tmp.exists() and not list(tmp.iterdir()) else None


if __name__ == "__main__":
    main()
