from typing import Optional
import logging
import ctypes
import asyncio
from OpenGL import GL
import numpy
from mediapipe.python.solutions import hands as mp_hands
from pydear import imgui as ImGui
from pydear import glo

logger = logging.getLogger(__name__)

FILE_DIALOG = 'ModalFileDialog'

VS = '''#version 330
in vec2 vPos;
void main()
{
    gl_Position = vec4(vPos, 0.0, 1.0);
}
'''

FS = '''#version 330
out vec4 FragColor;
void main()
{
    FragColor = vec4(1.0, 1.0, 1.0, 1.0);
}
'''


class Vertex(ctypes.Structure):
    _fields_ = [
        ('x', ctypes.c_float),
        ('y', ctypes.c_float),
    ]


class HandLandmark:
    def __init__(self) -> None:
        self.landmark = None
        self.clear_color = (ctypes.c_float * 4)(0.1, 0.2, 0.3, 1)
        self.fbo_manager = glo.FboRenderer()
        self.is_initialized = False
        self.vertices = (Vertex * 21)()
        self.is_updated = False

        self.capture_texture: Optional[glo.Texture] = None

    def show_table(self, p_open: ctypes.Array):
        if ImGui.Begin('hand', p_open):
            if self.landmark:
                flags = (
                    ImGui.ImGuiTableFlags_.BordersV
                    | ImGui.ImGuiTableFlags_.BordersOuterH
                    | ImGui.ImGuiTableFlags_.Resizable
                    | ImGui.ImGuiTableFlags_.RowBg
                    | ImGui.ImGuiTableFlags_.NoBordersInBody
                )

                if ImGui.BeginTable("tiles", 4, flags):
                    # header
                    # ImGui.TableSetupScrollFreeze(0, 1); // Make top row always visible
                    ImGui.TableSetupColumn('index')
                    ImGui.TableSetupColumn('x')
                    ImGui.TableSetupColumn('y')
                    ImGui.TableSetupColumn('z')
                    ImGui.TableHeadersRow()

                    # body
                    for i, p in enumerate(self.landmark):
                        ImGui.TableNextRow()
                        # index
                        ImGui.TableNextColumn()
                        ImGui.TextUnformatted(f'{i}')
                        #
                        ImGui.TableNextColumn()
                        ImGui.TextUnformatted(f'{p.x:.2f}')
                        ImGui.TableNextColumn()
                        ImGui.TextUnformatted(f'{p.y:.2f}')
                        ImGui.TableNextColumn()
                        ImGui.TextUnformatted(f'{p.z:.2f}')

                    ImGui.EndTable()
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
                self.update_capture_texture(image)

                results = hands.process(image)

                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        self.landmark = hand_landmarks.landmark

                        # update vertices
                        for i, v in enumerate(self.landmark):
                            self.vertices[i] = Vertex(v.x, v.y)
                        self.is_updated = True

    def update_capture_texture(self, image: numpy.ndarray):
        h, w = image.shape[:2]
        if not self.capture_texture or self.capture_texture.width != w or self.capture_texture.height != h:
            self.capture_texture = glo.Texture(
                w, h, image, pixel_type=GL.GL_RGB)
        else:
            self.capture_texture.update(0, 0, w, h, image)

    def show_view(self, p_open):
        ImGui.PushStyleVar_2(ImGui.ImGuiStyleVar_.WindowPadding, (0, 0))
        if ImGui.Begin("render target", p_open,
                       ImGui.ImGuiWindowFlags_.NoScrollbar |
                       ImGui.ImGuiWindowFlags_.NoScrollWithMouse):
            w, h = ImGui.GetContentRegionAvail()
            texture = self.fbo_manager.clear(
                int(w), int(h), self.clear_color)

            self.render()

            if texture:
                ImGui.BeginChild("_image_")
                ImGui.Image(texture, (w, h), (0, 1), (1, 0))
                ImGui.EndChild()
        ImGui.End()
        ImGui.PopStyleVar()

    def show_texture(self, p_open):
        if ImGui.Begin("capture", p_open):
            if self.capture_texture:
                ImGui.BeginChild("_capture_")
                ImGui.Image(ctypes.c_void_p(int(self.capture_texture.handle)), (self.capture_texture.width,
                            self.capture_texture.height), (0, 0), (1, 1))
                ImGui.EndChild()

        ImGui.End()

    def initialize(self) -> None:
        self.shader = glo.Shader.load(VS, FS)
        if not self.shader:
            return
        vbo = glo.Vbo()
        self.vao = glo.Vao(
            vbo, glo.VertexLayout.create_list(self.shader.program))
        self.vao.vbo.set_vertices(self.vertices, is_dynamic=True)

    def render(self):
        if not self.is_initialized:
            self.initialize()
            self.is_initialized = True

        if self.is_updated:
            self.vao.vbo.set_vertices(self.vertices, is_dynamic=True)
            self.is_updated = False

        if not self.shader:
            return
        with self.shader:
            self.vao.draw(21, topology=GL.GL_POINTS)


def main():
    logging.basicConfig(level=logging.DEBUG)
    from pydear.utils.loghandler import ImGuiLogHandler
    log_handler = ImGuiLogHandler()
    log_handler.setFormatter(logging.Formatter(
        '%(name)s:%(lineno)s[%(levelname)s]%(message)s'))
    log_handler.register_root()

    from pydear.utils import glfw_app
    app = glfw_app.GlfwApp('hello_docking')

    from pydear.utils import dockspace
    import ctypes

    hand_landmark = HandLandmark()

    views = [
        dockspace.Dock('texture', hand_landmark.show_texture,
                       (ctypes.c_bool * 1)(True)),
        dockspace.Dock('metrics', ImGui.ShowMetricsWindow,
                       (ctypes.c_bool * 1)(True)),
        dockspace.Dock('landmarks', hand_landmark.show_table,
                       (ctypes.c_bool * 1)(True)),
        dockspace.Dock('view', hand_landmark.show_view,
                       (ctypes.c_bool * 1)(True)),
        dockspace.Dock('log', log_handler.draw, (ctypes.c_bool * 1)(True)),
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
