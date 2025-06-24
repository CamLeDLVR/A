import streamlit as st
import urllib.request
from moviepy import VideoFileClip
import base64
import openai
import os
from tempfile import NamedTemporaryFile

# ---------------- OpenAI API Setup ----------------
API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = openai.OpenAI(api_key=API_KEY)

# ---------------- Utility Functions ----------------
def download_video(video_url):
    print("Downloading video...")
    tmp_file = NamedTemporaryFile(delete=False, suffix=".mp4")
    urllib.request.urlretrieve(video_url, tmp_file.name)
    return tmp_file.name

def extract_audio(video_path):
    print("Extracting audio from video...")
    tmp_audio = NamedTemporaryFile(delete=False, suffix=".wav")
    video = VideoFileClip(video_path).subclipped(0, min(27, VideoFileClip(video_path).duration))
    video.audio.write_audiofile(tmp_audio.name, codec='pcm_s16le', logger=None)
    print(f"Audio extracted to {tmp_audio.name}")
    print(f"Video Path: {video_path}")
    print("Cleaning up video file...")
    video.close()
    os.remove(video_path)
    return tmp_audio.name

def classify_accent(audio_path):
    with open(audio_path, "rb") as f:
        wav_bytes = f.read()
        encoded_string = base64.b64encode(wav_bytes).decode("utf-8")

    completion = openai_client.chat.completions.create(
        model="gpt-4o-audio-preview",
        modalities=["text", "audio"],
        audio={"voice": "alloy", "format": "wav"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """\
What is the English accent of this recording?
Answer MUST in this format:
accent: British
score: 0.99

If it is not English:
accent: None
score: 0"""
                    },
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": encoded_string,
                            "format": "wav"
                        }
                    }
                ]
            },
        ]
    )
    result = completion.choices[0].message.audio.transcript
    try:
        accent = result.split("accent:")[1].split('\n')[0].strip()
        score = float(result.split("score:")[1].strip())
    except Exception as e:
        return "Error", 0.0

    print("remove d audio file")
    os.remove(audio_path)

    if accent == "None" or score == 0.0:
        return "Not English", 0.0
    return accent, score

# ---------------- Streamlit UI ----------------
st.title("English Accent Classifier from Video")

video_url = st.text_input("Enter Video URL (.mp4 format):")

if st.button("Analyze") and video_url:
    with st.spinner("Downloading and processing..."):
        try:
            video_path = download_video(video_url)
            audio_path = extract_audio(video_path)
            accent, score = classify_accent(audio_path)
            lang = "English" if accent != "Not English" else "Not English"

            st.success("Analysis Complete!")
            st.write("**Language:**", lang)
            st.write("**Detected Accent:**", accent)
            st.write("**Confidence Score:**", f"{int(score * 100)}%")
        except Exception as e:
            st.error(f"Error: {e}")
else:
    st.info("Please enter a video URL (.mp4 format) and click Analyze.")
