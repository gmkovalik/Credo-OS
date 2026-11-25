// Credo "Today" desktop widget: a glass card with the saint, the day's colour and the next feast.
// Drag the card to move it; click it to open Today.
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as P5Support
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root
    property var day: ({})
    readonly property string command: "credo-liturgy --json"
    readonly property bool latin: Qt.locale().name.startsWith("la")

    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    toolTipMainText: day.title || ""

    // Shorter titles for the card ("Doctor of the Church" -> "Doctor")
    function shortTitle(s) {
        return (s || "").replace(/ of the Church$/, "").replace(/ et Ecclesiæ Doctoris$/, " et Doctoris")
                        .replace(/, Confessor and Doctor$/, ", Doctor");
    }

    P5Support.DataSource {
        id: exec
        engine: "executable"
        connectedSources: []
        onNewData: function (source, data) {
            if (source === root.command) {
                try { root.day = JSON.parse((data["stdout"] || "{}").trim()); } catch (e) {}
            }
            disconnectSource(source);
        }
        function run(cmd) { connectSource(cmd); }
    }
    Timer {
        interval: 10 * 60 * 1000; running: true; repeat: true; triggeredOnStart: true
        onTriggered: exec.run(root.command)
    }

    fullRepresentation: Item {
        Layout.preferredWidth: 300
        Layout.preferredHeight: 170
        Layout.minimumWidth: 240
        Layout.minimumHeight: 150

        GlassCard {
            anchors.fill: parent
            onActivated: exec.run("credo-library open /today")
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 5

            Text {
                text: root.latin ? "HODIE" : "HODIE · TODAY"
                color: Qt.rgba(1, 1, 1, 0.7)
                font.pixelSize: 11
                font.letterSpacing: 1.6
                font.weight: Font.DemiBold
            }
            Text {
                Layout.fillWidth: true
                text: root.day.saint ? root.shortTitle(root.day.saint) : (root.day.title || "…")
                color: "white"
                font.family: "Noto Serif"
                font.pixelSize: 18
                wrapMode: Text.WordWrap
                maximumLineCount: 3
                elide: Text.ElideRight
            }
            RowLayout {
                spacing: 7
                Rectangle {
                    width: 9; height: 9; radius: 4.5
                    color: root.day.color_hex || "#888"
                    border.color: Qt.rgba(1, 1, 1, 0.45)
                    border.width: 1.5
                }
                Text {
                    text: (root.day.season || "") + (root.day.color ? " · " + root.day.color : "")
                    color: Qt.rgba(1, 1, 1, 0.85)
                    font.pixelSize: 13
                }
            }
            Text {
                visible: !!root.day.next
                Layout.fillWidth: true
                elide: Text.ElideRight
                textFormat: Text.StyledText
                color: Qt.rgba(1, 1, 1, 0.85)
                font.pixelSize: 13
                text: root.day.next ? ((root.latin ? "Proxime: <b>" : "Next: <b>") + root.day.next.title + ", "
                      + Qt.formatDate(new Date(root.day.next.date + "T12:00:00"), "d MMM") + "</b>") : ""
            }
            Item { Layout.fillHeight: true }
        }
    }
}
