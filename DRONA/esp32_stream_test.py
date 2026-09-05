import cv2
import time

STREAM_URL = "http://192.168.4.1:81/stream"

print("Opening ESP32-CAM stream...")
print(STREAM_URL)

cap = cv2.VideoCapture(STREAM_URL)

if not cap.isOpened():
    raise RuntimeError("Could not open ESP32-CAM stream")

# May or may not be honored depending on backend,
# but harmless for this connectivity test.
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

print("Stream opened successfully.")
print("Press Q to quit.")

frames = 0
start_time = time.time()

while True:
    ok, frame = cap.read()

    if not ok or frame is None:
        print("Frame read failed")
        break

    frames += 1

    elapsed = time.time() - start_time
    fps = frames / elapsed if elapsed > 0 else 0

    cv2.putText(
        frame,
        f"ESP32 Stream | FPS: {fps:.1f}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )

    cv2.imshow("DronAI ESP32-CAM Test", frame)

    if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
        break

cap.release()
cv2.destroyAllWindows()

print("Stream closed.")