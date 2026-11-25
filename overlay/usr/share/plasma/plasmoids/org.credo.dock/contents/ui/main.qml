// Credo Dock: a glass dock with macOS-style magnification.
// Pinned apps and running windows come from Plasma's own task model (org.kde.taskmanager),
// so launching, switching and minimizing work like the standard task manager on Wayland.
// The panel it lives in is transparent; this widget draws the glass pill itself.
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

    readonly property real zoom: Plasmoid.configuration.magnification
    // Room above the pill for magnified icons. None when magnification is off (the default): then the
    // dock window is exactly the pill, so the blur KWin draws behind it is the pill, not a box.
    readonly property real headroom: zoom > 1.01 ? 10 : 0
    readonly property real spacing: 7
    readonly property real pad: 10
    // Icon size follows the panel: the magnified icon must fit inside it, so nothing is ever cut off.
    readonly property real base: Math.max(24, Math.min(Plasmoid.configuration.iconSize,
                                                       Math.floor((root.height - 2 * pad - headroom) / zoom)))
    property real mouseX: -10000          // pointer x inside the row, -10000 = away

    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    Plasmoid.constraintHints: Plasmoid.CanFillArea

    TaskManager.VirtualDesktopInfo { id: desktopInfo }
    TaskManager.ActivityInfo { id: activityInfo }
    TaskManager.TasksModel {
        id: tasks
        groupMode: TaskManager.TasksModel.GroupApplications
        sortMode: TaskManager.TasksModel.SortManual
        launchInPlace: true
        separateLaunchers: false
        hideActivatedLaunchers: true
        filterByVirtualDesktop: false
        filterByScreen: false
        filterByActivity: true
        activity: activityInfo.currentActivity
        virtualDesktop: desktopInfo.currentDesktop
        launcherList: Plasmoid.configuration.launchers
    }

    // Keep running apps in their pinned slot, like macOS (otherwise a newly opened window can be
    // appended at the end of the dock). Unpinned apps stay after the pinned ones, in their order.
    function desktopName(u) {
        var s = String(u || "").split("?")[0];
        s = s.substring(Math.max(s.lastIndexOf("/"), s.lastIndexOf(":")) + 1);
        return s;
    }
    function keepPinnedOrder() {
        var pins = (Plasmoid.configuration.launchers || []).map(desktopName);
        function key(i) {
            var u = tasks.data(tasks.makeModelIndex(i), TaskManager.AbstractTasksModel.LauncherUrlWithoutIcon);
            var p = pins.indexOf(desktopName(u));
            return p >= 0 ? p : 1000 + i;
        }
        var n = tasks.count;
        for (var pos = 0; pos < n; ++pos) {
            var best = pos, bestKey = key(pos);
            for (var j = pos + 1; j < n; ++j) {
                var k = key(j);
                if (k < bestKey) { best = j; bestKey = k; }
            }
            if (best !== pos) tasks.move(best, pos);
        }
    }
    // Click on an app, like macOS: start it if it is not running; otherwise bring its windows to the
    // front (restoring minimized ones). An app with several windows is a group in the task model,
    // and the model ignores "activate" on a group, so each window is raised, the last-used one last.
    function bringToFront(row) {
        var idx = tasks.makeModelIndex(row);
        var n = tasks.rowCount(idx);
        if (n <= 0) {                         // a launcher, or an app with a single window
            tasks.requestActivate(idx);
            return;
        }
        var last = 0, lastTime = -1;
        for (var c = 0; c < n; ++c) {
            var child = tasks.makeModelIndex(row, c);
            var t = tasks.data(child, TaskManager.AbstractTasksModel.LastActivated);
            var ms = t ? new Date(t).getTime() : 0;
            if (ms > lastTime) { lastTime = ms; last = c; }
        }
        for (var k = 0; k < n; ++k)
            if (k !== last) tasks.requestActivate(tasks.makeModelIndex(row, k));
        tasks.requestActivate(tasks.makeModelIndex(row, last));
    }

    Connections {
        target: tasks
        function onCountChanged() { Qt.callLater(root.keepPinnedOrder); }
        function onDataChanged() { Qt.callLater(root.keepPinnedOrder); }
    }

    P5Support.DataSource {
        id: exec
        engine: "executable"
        connectedSources: []
        onNewData: function (source) { disconnectSource(source); }
        function run(cmd) { connectSource(cmd); }
    }

    // How big an icon is, given its centre x: a smooth bump around the pointer.
    function scaleFor(cx) {
        var d = Math.abs(cx - root.mouseX);
        var range = root.base * 2.6;
        if (d >= range) return 1;
        return 1 + (root.zoom - 1) * (Math.cos(Math.PI * d / range) + 1) / 2;
    }

    fullRepresentation: Item {
        id: area
        // Reserve room for the widest (magnified) row, so the panel does not resize while zooming.
        readonly property real restWidth: row.restWidth + root.pad * 2
        Layout.preferredWidth: restWidth + root.base * (root.zoom - 1) * 2.2
        Layout.minimumWidth: Layout.preferredWidth
        // An explicit height: the pill plus room above it for magnified icons. (With fillHeight
        // alone the panel gave this item only a thin strip at the bottom, so hovering the icons
        // themselves was outside it.)
        Layout.minimumHeight: Math.ceil(root.base * root.zoom + root.pad * 2 + root.headroom)
        Layout.preferredHeight: Layout.minimumHeight
        Layout.fillHeight: true

        // ---- the glass pill
        Rectangle {
            id: pill
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 0
            anchors.horizontalCenter: parent.horizontalCenter
            width: root.headroom > 0 ? row.width + root.pad * 2 : parent.width   // fill the window: no blur outside the pill
            height: root.base + root.pad * 2
            radius: 26
            color: Qt.rgba(1, 1, 1, 0.17)   // flat glass, no gradient
            border.color: Qt.rgba(1, 1, 1, 0.32)
            border.width: 1
            Rectangle {                       // top-edge highlight, like Liquid Glass (inside the curve)
                anchors { left: parent.left; right: parent.right; top: parent.top
                          leftMargin: parent.radius; rightMargin: parent.radius; topMargin: 1 }
                height: 1
                color: Qt.rgba(1, 1, 1, 0.5)
            }
            Behavior on width { NumberAnimation { duration: 90 } }
        }

        // ---- icons
        Row {
            id: row
            anchors.bottom: pill.bottom
            anchors.bottomMargin: root.pad
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: root.spacing
            readonly property real restWidth: (tasks.count + 2) * root.base + (tasks.count + 2) * root.spacing + 18

            Repeater {
                model: tasks
                delegate: DockIcon {
                    restIndex: index
                    iconSource: model.decoration
                    label: model.display || ""
                    running: model.IsWindow === true || model.IsStartup === true
                    active: model.IsActive === true
                    onClicked: root.bringToFront(index)
                    onMiddleClicked: tasks.requestNewInstance(tasks.makeModelIndex(index))
                }
            }
            Rectangle {                       // divider, as in macOS before Downloads and the Trash
                width: 1; height: root.base * 0.8
                anchors.bottom: parent.bottom
                anchors.bottomMargin: root.base * 0.1
                color: Qt.rgba(1, 1, 1, 0.35)
            }
            DockIcon {
                restIndex: tasks.count + 0.25
                iconSource: "folder-download"
                label: i18nd("dolphin", "Downloads")
                onClicked: exec.run("sh -c 'xdg-open \"$(xdg-user-dir DOWNLOAD)\"'")
            }
            DockIcon {
                restIndex: tasks.count + 1.25
                iconSource: "user-trash-full"
                label: i18nd("dolphin", "Trash")
                onClicked: exec.run("dolphin trash:/")
            }
        }

        // Pointer position in "resting row" coordinates (icons unmagnified, row centred).
        HoverHandler {
            id: hover
            onPointChanged: root.mouseX = hover.hovered
                ? hover.point.position.x - (area.width - row.restWidth) / 2 : -10000
            onHoveredChanged: if (!hovered) root.mouseX = -10000
        }
    }

    component DockIcon: Item {
        id: icon
        property var iconSource
        property string label
        property bool running: false
        property bool active: false
        property real restIndex: 0          // position in the unmagnified row (avoids a binding loop on x)
        signal clicked()
        signal middleClicked()

        readonly property real s: root.scaleFor(restIndex * (root.base + root.spacing) + root.base / 2)
        property real shown: s              // animated copy of s (eases back when the pointer leaves)
        Behavior on shown { enabled: root.mouseX < -9000; NumberAnimation { duration: 140 } }
        width: root.base * shown
        height: root.base * shown
        anchors.bottom: parent ? parent.bottom : undefined

        Kirigami.Icon {
            anchors.fill: parent
            source: icon.iconSource
            active: iconHover.hovered
        }
        Rectangle {                           // running indicator
            visible: icon.running
            width: 5; height: 5; radius: 2.5
            color: icon.active ? "#e9c46a" : Qt.rgba(1, 1, 1, 0.85)
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.bottom
            anchors.topMargin: 3
        }
        PlasmaComponents3.ToolTip {
            text: icon.label
            visible: iconHover.hovered && icon.label !== ""
            delay: 150
        }
        // Passive handlers: unlike a hover-enabled MouseArea they don't hide the pointer from the
        // dock's own HoverHandler, so magnification follows the pointer over the icons.
        HoverHandler {
            id: iconHover
            cursorShape: Qt.PointingHandCursor
            // Report the pointer in resting-row coordinates, so magnification follows it over the icon
            onPointChanged: if (hovered && icon.width > 0)
                root.mouseX = icon.restIndex * (root.base + root.spacing)
                              + Math.max(0, Math.min(1, point.position.x / icon.width)) * root.base
        }
        TapHandler {
            acceptedButtons: Qt.LeftButton
            onTapped: icon.clicked()
        }
        TapHandler {
            acceptedButtons: Qt.MiddleButton
            onTapped: icon.middleClicked()
        }
    }
}
