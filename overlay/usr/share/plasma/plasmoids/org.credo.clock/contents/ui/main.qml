// Credo "Roman Clock" desktop widget: an analog face with Roman numerals (with the clockmaker's
// IIII), gold hands, the Church's name for the day (Dominica, Feria II ... Sabbatum) and the
// date in Roman numerals. Drag the card to move it; click it to open the liturgical calendar.
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as P5Support

PlasmoidItem {
    id: root
    property date now: new Date()
    readonly property var numerals: ["XII", "I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI"]
    readonly property var feriae: ["Dominica", "Feria II", "Feria III", "Feria IV", "Feria V", "Feria VI", "Sabbatum"]

    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    toolTipMainText: Qt.formatDateTime(now, "dddd d MMMM yyyy, hh:mm")

    function roman(n) {
        var out = "", table = [[1000, "M"], [900, "CM"], [500, "D"], [400, "CD"], [100, "C"], [90, "XC"],
                               [50, "L"], [40, "XL"], [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"]];
        for (var i = 0; i < table.length; i++)
            while (n >= table[i][0]) { out += table[i][1]; n -= table[i][0]; }
        return out;
    }

    P5Support.DataSource {
        id: exec
        engine: "executable"
        connectedSources: []
        onNewData: function (source) { disconnectSource(source); }
        function run(cmd) { connectSource(cmd); }
    }
    Timer { interval: 1000; running: true; repeat: true; onTriggered: root.now = new Date() }

    fullRepresentation: Item {
        Layout.preferredWidth: 170
        Layout.preferredHeight: 170
        Layout.minimumWidth: 130
        Layout.minimumHeight: 130

        GlassCard {
            anchors.fill: parent
            onActivated: exec.run("credo-library open /calendar")
        }

        Item {
            id: face
            anchors.centerIn: parent
            width: Math.min(parent.width, parent.height) - 22
            height: width
            readonly property real r: width / 2

            Rectangle {                                   // dial ring
                anchors.fill: parent
                radius: width / 2
                color: Qt.rgba(0, 0, 0, 0.12)
                border.color: Qt.rgba(1, 1, 1, 0.35)
                border.width: 1
            }
            Repeater {                                    // minute ticks
                model: 60
                Rectangle {
                    id: tick
                    required property int index
                    readonly property bool hour: index % 5 === 0
                    width: 1; height: 3
                    visible: !hour
                    color: Qt.rgba(1, 1, 1, 0.35)
                    x: face.r - width / 2
                    y: 3
                    transform: Rotation { origin.x: tick.width / 2; origin.y: face.r - 3; angle: tick.index * 6 }
                }
            }
            Repeater {                                    // Roman numerals
                model: 12
                Text {
                    readonly property real a: index * Math.PI / 6
                    text: root.numerals[index]
                    color: "white"
                    font.family: "Noto Serif"
                    font.pixelSize: Math.max(9, Math.round(face.r * 0.17))
                    x: face.r + Math.sin(a) * face.r * 0.76 - width / 2
                    y: face.r - Math.cos(a) * face.r * 0.76 - height / 2
                }
            }
            Text {                                        // the Church's name for the day
                anchors.horizontalCenter: parent.horizontalCenter
                y: face.r * 1.30
                text: root.feriae[root.now.getDay()].toUpperCase()
                color: "#e9c46a"
                font.pixelSize: Math.max(7, Math.round(face.r * 0.10))
                font.letterSpacing: 1
            }
            Text {                                        // date in Roman numerals: day · month
                anchors.horizontalCenter: parent.horizontalCenter
                y: face.r * 0.52
                text: root.roman(root.now.getDate()) + " · " + root.roman(root.now.getMonth() + 1)
                color: Qt.rgba(1, 1, 1, 0.75)
                font.family: "Noto Serif"
                font.pixelSize: Math.max(7, Math.round(face.r * 0.10))
            }

            component Hand: Rectangle {
                id: hand
                property real deg                         // not "angle": Rotation has its own
                property real length
                antialiasing: true
                radius: width / 2
                x: face.r - width / 2
                y: face.r - length
                height: length + width
                transform: Rotation { origin.x: hand.width / 2; origin.y: hand.length; angle: hand.deg }
            }
            Hand {                                        // hours
                width: 4; length: face.r * 0.48; color: "#e9c46a"
                deg: (root.now.getHours() % 12 + root.now.getMinutes() / 60) * 30
            }
            Hand {                                        // minutes
                width: 3; length: face.r * 0.70; color: "#f6dc86"
                deg: (root.now.getMinutes() + root.now.getSeconds() / 60) * 6
            }
            Hand {                                        // seconds
                width: 1; length: face.r * 0.78; color: Qt.rgba(1, 1, 1, 0.8)
                deg: root.now.getSeconds() * 6
            }
            Rectangle {
                width: 8; height: 8; radius: 4; color: "#e9c46a"
                anchors.centerIn: parent
            }
        }
    }
}
