import cv2
import mediapipe as mp
import numpy as np
import math

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not cap.isOpened():
    print("Camera not working")
    exit()

def calculate_distance(point1, point2):
    return math.sqrt(
        (point2.x - point1.x) ** 2 +
        (point2.y - point1.y) ** 2
    )

while True:

    success, img = cap.read()

    if not success:
        print("Failed to capture")
        break

    img = cv2.flip(img, 1)

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    results = hands.process(rgb)

    gesture = "Unknown"

    if results.multi_hand_landmarks:

        for hand_landmarks in results.multi_hand_landmarks:

            lm = hand_landmarks.landmark

            thumb_tip = lm[4]
            index_tip = lm[8]
            middle_tip = lm[12]
            ring_tip = lm[16]
            pinky_tip = lm[20]

            wrist = lm[0]

            thumb_distance = calculate_distance(thumb_tip, wrist)
            index_distance = calculate_distance(index_tip, wrist)
            middle_distance = calculate_distance(middle_tip, wrist)
            ring_distance = calculate_distance(ring_tip, wrist)
            pinky_distance = calculate_distance(pinky_tip, wrist)

            open_fingers = 0

            if thumb_distance > 0.25:
                open_fingers += 1

            if index_distance > 0.3:
                open_fingers += 1

            if middle_distance > 0.3:
                open_fingers += 1

            if ring_distance > 0.3:
                open_fingers += 1

            if pinky_distance > 0.3:
                open_fingers += 1

            # Gesture Detection

            if open_fingers == 0:
                gesture = "FIST"

            elif open_fingers == 5:
                gesture = "PALM"

            elif open_fingers == 2:
                gesture = "PEACE"

            elif thumb_distance > 0.3 and open_fingers == 1:
                gesture = "THUMBS UP"

            else:
                gesture = "GESTURE DETECTED"

            mp_draw.draw_landmarks(
                img,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS
            )

    cv2.putText(
        img,
        f'Gesture: {gesture}',
        (20, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    cv2.imshow("Hand Gesture Recognition", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()