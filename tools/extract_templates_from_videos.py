import cv2
import os

VIDEOS = {
    "pre_jogo": [
        "videos/Aquecimento_prejogo.mp4",
        "videos/Anuncio de pre_jogo.mp4",
        "videos/pre_jogo.mp4",
        "videos/Escalação_Preapito inicial.mp4",
    ],
    "jogo": [
        "videos/Jogo ao vivo_primeiro tempo.mp4",
        "videos/Jogo ao vivo_segundo tempo.mp4",
        "videos/momento_GOL.mp4",
    ],
    "intervalo": [
        "videos/Intervalo.mp4",
        "videos/Pos jogo.mp4",
    ],
}

OUTPUT_DIR = "templates"

# ROI do placar (ajustável)
ROI = {
    "x": 0,
    "y": 0,
    "w": 350,
    "h": 120
}


def extract(video_path, category, index_start=1):

    cap = cv2.VideoCapture(video_path)

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    samples = [
        int(frame_count * 0.2),
        int(frame_count * 0.5),
        int(frame_count * 0.8),
    ]

    i = index_start

    for s in samples:

        cap.set(cv2.CAP_PROP_POS_FRAMES, s)
        ret, frame = cap.read()

        if not ret:
            continue

        x = ROI["x"]
        y = ROI["y"]
        w = ROI["w"]
        h = ROI["h"]

        crop = frame[y:y+h, x:x+w]

        out_dir = os.path.join(OUTPUT_DIR, category)
        os.makedirs(out_dir, exist_ok=True)

        path = os.path.join(out_dir, f"{category}_{i:02d}.png")

        cv2.imwrite(path, crop)

        print("saved:", path)

        i += 1

    cap.release()

    return i


def main():

    for category, vids in VIDEOS.items():

        i = 1

        for v in vids:
            if not os.path.exists(v):
                print("missing:", v)
                continue

            i = extract(v, category, i)


if __name__ == "__main__":
    main()