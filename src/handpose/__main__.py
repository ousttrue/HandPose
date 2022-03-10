import logging
from pydear.utils import filedialog
logger = logging.getLogger(__name__)

FILE_DIALOG = 'ModalFileDialog'


def main():
    logging.basicConfig(level=logging.DEBUG)

    from pydear.utils import glfw_app
    app = glfw_app.GlfwApp('hello_docking')

    from pydear.utils import dockspace
    from pydear import imgui as ImGui
    import ctypes

    def show_hello(p_open):
        if ImGui.Begin('hello', p_open):
            ImGui.TextUnformatted('hello text')
            ImGui.SliderFloat4('clear color', app.clear_color, 0, 1)
            ImGui.ColorPicker4('color', app.clear_color)
        ImGui.End()
    views = [
        dockspace.Dock('demo', ImGui.ShowDemoWindow,
                       (ctypes.c_bool * 1)(True)),
        dockspace.Dock('metrics', ImGui.ShowMetricsWindow,
                       (ctypes.c_bool * 1)(True)),
        dockspace.Dock('hello', show_hello,
                       (ctypes.c_bool * 1)(True)),
    ]

    def menu():
        if ImGui.BeginMenu(b"File", True):
            if ImGui.MenuItem('open'):
                filedialog.open(FILE_DIALOG)
            ImGui.EndMenu()

    def modal():
        selected = filedialog.modal(FILE_DIALOG)
        if selected:
            print(f'select: {selected}')

    gui = dockspace.DockingGui(app.loop, docks=views, menu=menu, modal=modal)

    from pydear.backends.impl_glfw import ImplGlfwInput
    impl_glfw = ImplGlfwInput(app.window)

    while app.clear():
        impl_glfw.process_inputs()
        gui.render()
    del gui


if __name__ == '__main__':
    main()
