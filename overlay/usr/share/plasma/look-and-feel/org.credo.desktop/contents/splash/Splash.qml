import QtQuick

Rectangle {
    id: root
    color: "#14110d"
    property int stage

    Image {
        id: logo
        anchors.centerIn: parent
        anchors.verticalCenterOffset: -height * 0.2
        source: "file:///usr/share/credo/theme/splash-logo.svg"
        width: Math.min(root.width, root.height) * 0.16
        height: width
        sourceSize.width: width
        sourceSize.height: height
        opacity: 0.0
        OpacityAnimator on opacity { from: 0; to: 1; duration: 900; running: true }
    }

    Text {
        anchors.top: logo.bottom
        anchors.topMargin: logo.height * 0.25
        anchors.horizontalCenter: parent.horizontalCenter
        text: "CREDO IN UNUM DEUM"
        color: "#c9a85a"
        font.family: "Noto Serif"
        font.pixelSize: Math.max(14, root.height * 0.022)
        font.letterSpacing: 6
    }

    Rectangle {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: root.height * 0.12
        anchors.horizontalCenter: parent.horizontalCenter
        width: root.width * 0.18
        height: 3
        radius: 2
        color: "#3a3329"
        Rectangle {
            width: parent.width * Math.min(1, root.stage / 6)
            height: parent.height
            radius: 2
            color: "#c9a85a"
            Behavior on width { NumberAnimation { duration: 400 } }
        }
    }
}
