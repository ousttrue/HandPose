import logging
import ctypes
import asyncio
from pydear import imgui as ImGui
from mediapipe.python.solutions import hands as mp_hands

logger = logging.getLogger(__name__)

FILE_DIALOG = 'ModalFileDialog'


class HandLandmark:
    def __init__(self) -> None:
        self.landmark = None

    def show(self, p_open: ctypes.Array):
        if ImGui.Begin('hand', p_open):
            if self.landmark:
                for e, mark in zip(mp_hands.HandLandmark, self.landmark):
                    ImGui.TextUnformatted(
                        f'{e.name}, {mark.x}, {mark.y}, {mark.z}')
                    pass
            # ImGui.SliderFloat4('clear color', app.clear_color, 0, 1)
            # ImGui.ColorPicker4('color', app.clear_color)
        ImGui.End()

    async def estimate(self):
        import cv2
        cap = cv2.VideoCapture(0)
        with mp_hands.Hands(
                model_complexity=0,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5) as hands:
            while True:
                success, image = await asyncio.to_thread(cap.read)
                if not success:
                    print("Ignoring empty camera frame.")
                    continue

                # To improve performance, optionally mark the image as not writeable to
                # pass by reference.
                image.flags.writeable = False
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                results = hands.process(image)

                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        self.landmark = hand_landmarks.landmark


def main():
    logging.basicConfig(level=logging.DEBUG)

    from pydear.utils import glfw_app
    app = glfw_app.GlfwApp('hello_docking')

    from pydear.utils import dockspace
    import ctypes

    hand_landmark = HandLandmark()

    views = [
        dockspace.Dock('handlandmark', hand_landmark.show,
                       (ctypes.c_bool * 1)(True)),
    ]

    gui = dockspace.DockingGui(app.loop, docks=views)

    app.loop.create_task(hand_landmark.estimate())

    from pydear.backends.impl_glfw import ImplGlfwInput
    impl_glfw = ImplGlfwInput(app.window)

    while app.clear():
        impl_glfw.process_inputs()
        gui.render()
    del gui


if __name__ == '__main__':
    main()
