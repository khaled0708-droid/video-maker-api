import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import cloudinary
import cloudinary.uploader
import numpy as np
from moviepy import ImageClip, TextClip, CompositeVideoClip, concatenate_videoclips
import moviepy.video.fx as fx
from PIL import Image

cloudinary.config(
    cloud_name = "khaledtn", 
    api_key = "948831227617247", 
    api_secret = "kkjEpD7pbYaNdlpkPsU2V2Pt0pk", 
    secure = True
)

imagemagick_path = r"C:\Users\azerty\Desktop\ImageMagick\magick.exe"
os.environ["IMAGEMAGICK_BINARY"] = imagemagick_path
cars_folder = r"C:\Users\azerty\Desktop\voitures"

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

@app.route('/make_video', methods=['POST'])
def start_production():
    try:
        data = request.json
        print("=" * 50)
        print("Request received from FlutterFlow")
        print(f"Data: {data}")
        print("=" * 50)

        video_title = data.get('scenario', 'Ai_Film').replace(" ", "_")

        if not os.path.exists(cars_folder):
            return jsonify({
                "status": "Error",
                "message": "Folder not found",
                "video_url": "",
                "video_title": ""
            }), 500

        images = [f for f in os.listdir(cars_folder) 
                  if f.endswith(('.jpg', '.png', '.jpeg'))]

        if not images:
            return jsonify({
                "status": "Error",
                "message": "No images found",
                "video_url": "",
                "video_title": ""
            }), 500

        all_clips = []
        for img_name in images:
            img_path = os.path.join(cars_folder, img_name)
            print(f"Processing: {img_name}")

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

        output_path = os.path.join(os.path.expanduser("~"), "Desktop", f"{video_title}.mp4")
        final_video = concatenate_videoclips(all_clips, method="compose")

        print("Saving video...")
        final_video.write_videofile(output_path, fps=24, codec="libx264")

        print("Uploading to Cloudinary...")
        upload_result = cloudinary.uploader.upload(
            output_path,
            public_id=video_title,
            resource_type="video",
            chunk_size=6000000
        )

        secure_url = upload_result.get('secure_url')
        print(f"Success! URL: {secure_url}")

        return jsonify({
            "status": "Success",
            "message": "Video created successfully",
            "video_url": secure_url,
            "video_title": video_title
        }), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            "status": "Error",
            "message": str(e),
            "video_url": "",
            "video_title": ""
        }), 500

if __name__ == '__main__':
    print("=" * 60)
    print("Server running on port 8080")
    print("http://192.168.1.110:8080/make_video")
    print("=" * 60)
    app.run(host='0.0.0.0', port=8080, threaded=True)