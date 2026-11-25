// The Credo menu: the logo at the top left of the menu bar, like the Apple menu.
// Its popup is drawn by the Plasma style's glass dialog background.
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.plasma5support as P5Support
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root
    readonly property bool latin: Qt.locale().name.startsWith("la")
    function tr(en, la) { return latin ? la : en }

    preferredRepresentation: compactRepresentation
    switchWidth: Kirigami.Units.gridUnit * 10
    switchHeight: Kirigami.Units.gridUnit * 10

    P5Support.DataSource {
        id: exec
        engine: "executable"
        connectedSources: []
        onNewData: function (source) { disconnectSource(source); }
        function run(cmd) { root.expanded = false; connectSource(cmd); }
    }

    // The Chi-Rho glyph in the menu bar's text colour: white on a dark bar, black on a light one.
    compactRepresentation: MouseArea {
        id: button
        Layout.minimumWidth: 40
        Layout.preferredWidth: Layout.minimumWidth
        hoverEnabled: true
        onClicked: root.expanded = !root.expanded

        // Credo's own menu-bar band: a dark glass tint across the whole top bar, behind every widget.
        // Drawn here (this button is only ever in the top bar) rather than by the Plasma style, which
        // the dock shares, so the dock never gets a box. It is moved to the panel window's root item.
        Rectangle {
            id: barTint
            z: -1000
            color: Qt.rgba(0.05, 0.08, 0.06, 0.42)
            Rectangle {                               // hairline along the bottom edge, like macOS
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                height: 1
                color: Qt.rgba(1, 1, 1, 0.08)
            }
            Component.onCompleted: {
                var p = button;
                while (p.parent)
                    p = p.parent;
                parent = p;
                anchors.fill = p;
            }
        }

        Rectangle {                                   // soft glass highlight on hover / while open
            anchors.centerIn: parent
            width: parent.width; height: Math.min(parent.height - 4, 24)
            radius: height / 2
            color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b,
                           root.expanded ? 0.18 : button.containsMouse ? 0.10 : 0)
            Behavior on color { ColorAnimation { duration: 120 } }
        }
        Image {
            anchors.centerIn: parent
            height: Math.min(parent.height - 8, 22)          // like the Apple logo: clear, not tiny
            width: height                                    // the Chi-Rho in its ring is round
            sourceSize: Qt.size(width * 3, height * 3)       // crisp on HiDPI screens
            fillMode: Image.PreserveAspectFit
            smooth: true
            // white on a dark menu bar, black on a light one (follows the colour scheme's text colour)
            source: Kirigami.Theme.textColor.hslLightness > 0.5
                    ? "/usr/share/credo/logos/chirho-ring-white.svg"
                    : "/usr/share/credo/logos/chirho-ring-black.svg"
        }
    }

    fullRepresentation: ColumnLayout {
        Layout.preferredWidth: Kirigami.Units.gridUnit * 15
        Layout.minimumWidth: Layout.preferredWidth
        spacing: 0

        component Entry: PlasmaComponents3.ItemDelegate {
            id: entry
            property string command
            property string shortcut
            Layout.fillWidth: true
            contentItem: RowLayout {
                spacing: Kirigami.Units.smallSpacing
                Kirigami.Icon { source: entry.icon.name; Layout.preferredWidth: 18; Layout.preferredHeight: 18 }
                PlasmaComponents3.Label { text: entry.text; Layout.fillWidth: true }
                PlasmaComponents3.Label { text: entry.shortcut; opacity: 0.55 }
            }
            onClicked: exec.run(entry.command)
        }
        component Sep: Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 8; Layout.rightMargin: 8
            Layout.topMargin: 4; Layout.bottomMargin: 4
            height: 1
            color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.15)
        }

        Entry { text: root.tr("About Credo OS", "De Credo OS"); icon.name: "credo"; command: "credo-center --welcome" }
        Sep {}
        Entry { text: root.tr("Apps", "Applicationes"); icon.name: "credo-launchpad"; command: "credo-launchpad" }
        Entry { text: "Credo Center"; icon.name: "credo-center"; command: "credo-center" }
        Entry { text: root.tr("Software…", "Programmata…"); icon.name: "org.kde.discover"; command: "plasma-discover" }
        Entry { text: root.tr("System Settings…", "Optiones systematis…"); icon.name: "preferences-system"; command: "systemsettings" }
        Sep {}
        Entry { text: root.tr("Today", "Hodie"); icon.name: "credo-today"; command: "credo-library open /today" }
        Entry { text: root.tr("Holy Rosary", "Sanctissimum Rosarium"); icon.name: "credo-rosary"; command: "credo-library open /rosary" }
        Sep {}
        Entry { text: root.tr("Lock Screen", "Obsera"); icon.name: "system-lock-screen"; command: "loginctl lock-session"; shortcut: "Meta+L" }
        Entry { text: root.tr("Sleep", "Dormi"); icon.name: "system-suspend"; command: "systemctl suspend" }
        Entry { text: root.tr("Restart…", "Iterum incipe…"); icon.name: "system-reboot"; command: "dbus-send --session --type=method_call --dest=org.kde.LogoutPrompt /LogoutPrompt org.kde.LogoutPrompt.promptReboot" }
        Entry { text: root.tr("Shut Down…", "Exstingue…"); icon.name: "system-shutdown"; command: "dbus-send --session --type=method_call --dest=org.kde.LogoutPrompt /LogoutPrompt org.kde.LogoutPrompt.promptShutDown" }
        Sep {}
        Entry { text: root.tr("Log Out…", "Exi…"); icon.name: "system-log-out"; command: "dbus-send --session --type=method_call --dest=org.kde.LogoutPrompt /LogoutPrompt org.kde.LogoutPrompt.promptLogout" }
    }
}
