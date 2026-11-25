// Credo "Holy Rosary" desktop widget: today's mysteries on a glass card.
// Drag the card to move it; click it to pray.
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as P5Support
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root
    property string mysteries: ""
    readonly property string command: "credo-liturgy --json"
    readonly property bool latin: Qt.locale().name.startsWith("la")

    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    P5Support.DataSource {
        id: exec
        engine: "executable"
        connectedSources: []
        onNewData: function (source, data) {
            if (source === root.command) {
                try { root.mysteries = JSON.parse((data["stdout"] || "{}").trim()).rosary || ""; } catch (e) {}
            }
            disconnectSource(source);
        }
        function run(cmd) { connectSource(cmd); }
    }
    Timer {
        interval: 30 * 60 * 1000; running: true; repeat: true; triggeredOnStart: true
        onTriggered: exec.run(root.command)
    }

    fullRepresentation: Item {
        Layout.preferredWidth: 170
        Layout.preferredHeight: 170
        Layout.minimumWidth: 140
        Layout.minimumHeight: 140

        GlassCard {
            anchors.fill: parent
            onActivated: exec.run("credo-library open /rosary")
        }
        ColumnLayout {
            anchors.centerIn: parent
            width: parent.width - 24
            spacing: 6
            Kirigami.Icon {
                source: "credo-rosary"
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 64
                Layout.preferredHeight: 64
            }
            Text {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: root.mysteries.replace(/^The /, "")
                color: "white"
                font.pixelSize: 13
                font.weight: Font.Bold
                wrapMode: Text.WordWrap
            }
            Text {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: root.latin ? "Preme ut ores" : "Tap to pray"
                color: Qt.rgba(1, 1, 1, 0.7)
                font.pixelSize: 12
            }
        }
    }
}
