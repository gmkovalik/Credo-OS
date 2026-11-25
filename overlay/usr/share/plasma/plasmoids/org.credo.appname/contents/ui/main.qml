// The active application's name in bold, next to the Credo logo, as in the macOS menu bar.
// On the desktop (no active window) it shows "Credo". Clicking it opens Credo Center.
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.plasma5support as P5Support
import org.kde.taskmanager as TaskManager
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root
    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    TaskManager.VirtualDesktopInfo { id: desktopInfo }
    TaskManager.ActivityInfo { id: activityInfo }
    TaskManager.TasksModel {
        id: tasks
        groupMode: TaskManager.TasksModel.GroupDisabled
        filterByVirtualDesktop: true
        filterByActivity: true
        virtualDesktop: desktopInfo.currentDesktop
        activity: activityInfo.currentActivity
    }
    property string appName: "Credo"
    function refresh() {
        var i = tasks.activeTask;
        var name = (i && i.valid) ? tasks.data(i, TaskManager.AbstractTasksModel.AppName) : "";
        root.appName = name && name.length ? name : "Credo";
    }
    Connections {
        target: tasks
        function onActiveTaskChanged() { root.refresh() }
        function onDataChanged() { root.refresh() }
        function onCountChanged() { root.refresh() }
    }
    Component.onCompleted: refresh()

    P5Support.DataSource {
        id: exec
        engine: "executable"
        connectedSources: []
        onNewData: function (source) { disconnectSource(source); }
    }

    fullRepresentation: MouseArea {
        Layout.minimumWidth: label.implicitWidth + Kirigami.Units.smallSpacing * 2
        Layout.preferredWidth: Layout.minimumWidth
        Layout.fillHeight: true
        onClicked: exec.connectSource("credo-center")
        PlasmaComponents3.Label {
            id: label
            anchors.centerIn: parent
            text: root.appName
            font.weight: Font.Bold
            font.pixelSize: 14
            elide: Text.ElideRight
        }
    }
}
