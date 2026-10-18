"""Merge identical consecutive GIF frames and cap how long any one frame is held.

Used after `vhs docs/demo.tape` so long API waits do not dominate the GIF:

    uv run --with pillow python scripts/squash_gif.py docs/demo.gif docs/demo.gif 1500 8000
"""
import sys
from PIL import Image, ImageChops

src, dst = sys.argv[1], sys.argv[2]
max_hold_ms, final_hold_ms = int(sys.argv[3]), int(sys.argv[4])

im = Image.open(src)
frames, durations = [], []
for i in range(im.n_frames):
    im.seek(i)
    frame = im.convert("RGB")
    d = im.info.get("duration", 40)
    box = ImageChops.difference(frame, frames[-1]).getbbox() if frames else (0, 0, 9999, 9999)
    # A change no bigger than the blinking cursor is not a real change
    if box is None or (box[2] - box[0]) * (box[3] - box[1]) <= 40 * 40:
        durations[-1] += d
    else:
        frames.append(frame)
        durations.append(d)

durations = [min(d, max_hold_ms) for d in durations]
durations[-1] = final_hold_ms
frames[0].save(dst, save_all=True, append_images=frames[1:], duration=durations,
               loop=0, optimize=True, disposal=1)
print(f"{im.n_frames} frames -> {len(frames)}, {sum(durations)/1000:.1f}s")
