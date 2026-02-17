import os
import tempfile
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import cloudinary
import cloudinary.uploader
import numpy as np
from moviepy import ImageClip, TextClip, CompositeVideoClip, concatenate_videoclips
import moviepy.video.fx as fx
from PIL import Image
from io import BytesIO

# تكوين Cloudinary من المتغيرات البيئية
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME', 'khaledtn'),
    api_key=os.environ.get('CLOUDINARY_API_KEY', '948831227617247'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET', 'kkjEpD7pbYaNdlpkPsU2V2Pt0pk'),
    secure=True
)

app = Flask(__name__)
CORS(app)

def zoom_in_effect(clip, zoom_ratio=0.04):
    def effect(get_frame, t):
        img = get_frame(t)
        base_size = img.shape[:2]
        new_size = [
            int(base_size[0] * (1 + zoom_ratio * (t / clip.duration))),
            int(base_size[1] * (1 + zoom_ratio * (t / clip.duration)))
        ]
        pil_img = Image.fromarray(img)
        resized_img = pil_img.resize((new_size[1], new_size[0]), Image.LANCZOS)
        left = (new_size[1] - base_size[1]) / 2
        top = (new_size[0] - base_size[0]) / 2
        return np.array(resized_img.crop((left, top, left + base_size[1], top + base_size[0])))
    return clip.transform(effect)

def download_image(url):
    """تحميل صورة من رابط وحفظها في ملف مؤقت"""
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        img = Image.open(BytesIO(response.content))
        # حفظ الصورة بصيغة PNG في ملف مؤقت
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        img.save(temp_file.name)
        return temp_file.name
    else:
        raise Exception(f"Failed to download image from {url}")

@app.route('/make_video', methods=['POST'])
def start_production():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "Error", "message": "Invalid JSON"}), 400

        scenario = data.get('scenario', 'Ai_Film').replace(" ", "_")
        image_urls = data.get('image_urls', [])

        if not image_urls:
            return jsonify({"status": "Error", "message": "No image URLs provided"}), 400

        # مجلد مؤقت لتحميل الصور
        temp_dir = tempfile.mkdtemp()
        image_paths = []

        # تحميل كل صورة من الرابط
        for idx, url in enumerate(image_urls):
            try:
                img_path = download_image(url)
                image_paths.append(img_path)
                print(f"Downloaded {url} to {img_path}")
            except Exception as e:
                print(f"Error downloading image {idx}: {str(e)}")
                continue

        if not image_paths:
            return jsonify({"status": "Error", "message": "No valid images after downloading"}), 400

        # إنشاء مقاطع الفيديو (نفس الكود السابق)
        all_clips = []
        for img_path in image_paths:
            clip = ImageClip(img_path, duration=5).resized(height=720)
            if clip.w % 2 != 0:
                clip = clip.resized(width=clip.w - 1)

            clip = zoom_in_effect(clip)

            txt = TextClip(
                text="LUXURY EXCLUSIVE",
                font_size=70,
                color='gold',
                method='label'
            ).with_duration(5).with_position(('center', 600)).with_effects([fx.FadeIn(1)])

            all_clips.append(
                CompositeVideoClip([clip, txt]).with_effects([fx.FadeIn(1), fx.FadeOut(1)])
            )

        # حفظ الفيديو النهائي
        output_path = os.path.join(temp_dir, f"{scenario}.mp4")
        final_video = concatenate_videoclips(all_clips, method="compose")
        final_video.write_videofile(output_path, fps=24, codec="libx264")

        # رفع إلى Cloudinary
        upload_result = cloudinary.uploader.upload(
            output_path,
            public_id=scenario,
            resource_type="video",
            chunk_size=6000000
        )

        secure_url = upload_result.get('secure_url')

        # تنظيف الملفات المؤقتة
        for path in image_paths + [output_path]:
            try:
                os.remove(path)
            except:
                pass
        os.rmdir(temp_dir)

        return jsonify({
            "status": "Success",
            "message": "Video created successfully",
            "video_url": secure_url,
            "video_title": scenario
        }), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            "status": "Error",
            "message": str(e),
            "video_url": "",
            "video_title": ""
        }), 500

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Video Maker API is running"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, threaded=True)
