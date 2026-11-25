import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.plasma5support as P5Support
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root

    property string season: "…"
    property string colorHex: "#888888"
    property string dayTitle: ""
    readonly property string command: "credo-liturgy --plain"

    toolTipMainText: dayTitle
    toolTipSubText: season

    P5Support.DataSource {
        id: exec
        engine: "executable"
        connectedSources: []
        onNewData: function (source, data) {
            var lines = (data["stdout"] || "").trim().split("\n");
            if (source === root.command && lines.length >= 3) {
                root.season = lines[0];
                root.colorHex = lines[1];
                root.dayTitle = lines[2];
            }
            disconnectSource(source);
        }
        function run(cmd) { connectSource(cmd); }
    }

    Timer {
        interval: 15 * 60 * 1000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: exec.run(root.command)
    }

    // In the menu bar: a small glass pill with the colour dot and the day (macOS 26 style).
    compactRepresentation: Item {
        Layout.minimumWidth: pill.width + Kirigami.Units.smallSpacing
        Layout.preferredWidth: Layout.minimumWidth
        Rectangle {
            id: pill
            anchors.centerIn: parent
            height: Math.min(parent.height - 4, 22)
            width: row.implicitWidth + 20
            radius: height / 2
            visible: Plasmoid.formFactor !== PlasmaCore.Types.Vertical
            color: Qt.rgba(1, 1, 1, 0.16)   // flat glass, no gradient
            border.color: Qt.rgba(1, 1, 1, 0.30)
            border.width: 1
        }
        RowLayout {
            id: row
            anchors.centerIn: parent
            spacing: 7
            Rectangle {
                width: 9; height: 9; radius: 4.5
                color: root.colorHex
                border.color: Qt.rgba(1, 1, 1, 0.45)
                border.width: 1.5
            }
            PlasmaComponents3.Label {
                text: Plasmoid.formFactor === PlasmaCore.Types.Vertical ? "" : (root.dayTitle || root.season)
                font.pixelSize: 13
                elide: Text.ElideRight
                Layout.maximumWidth: 360
            }
        }
        MouseArea {
            anchors.fill: parent
            onClicked: root.expanded = !root.expanded
        }
    }

    fullRepresentation: ColumnLayout {
        Layout.preferredWidth: Kirigami.Units.gridUnit * 18
        spacing: Kirigami.Units.smallSpacing
        Kirigami.Heading {
            level: 3
            text: root.dayTitle
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
        RowLayout {
            Rectangle { width: 14; height: 14; radius: 7; color: root.colorHex }
            PlasmaComponents3.Label { text: root.season }
        }
        PlasmaComponents3.Button {
            text: "Missa diei / Mass of the Day"
            icon.name: "view-calendar-day"
            onClicked: exec.run("credo-library open /mass")
        }
        PlasmaComponents3.Button {
            text: "Bibliotheca / Library"
            icon.name: "bookmarks"
            onClicked: exec.run("credo-library open /")
        }
    }
}
