import QtQuick 2.15
import QtQuick.Controls 2.15

ApplicationWindow {
    id: splashWindow
    visible: true
    width: 800
    height: 650  // Increased height to accommodate the label
    flags: Qt.SplashScreen
    color: "#282a36"  // Dark background from qdarktheme

    // Property to bind to Python progress
    property real progressValue: 0

    // Icon at the top
    Image {
        id: icon
        source: "file:///D:/Desktop/MyNews/AMFLogo1-wm.png"  // Replace with your icon path
        width: 400
        height: 400
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 20
    }

    // Circular progress bar using Canvas
    Canvas {
        id: progressCircle
        width: 150
        height: 150
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: icon.bottom
        anchors.topMargin: 20    // 20px padding between logo and progress bar

        onPaint: {
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);

            var centerX = width / 2;
            var centerY = height / 2;
            var radius = Math.min(width, height) / 2 - 10;
            var startAngle = -Math.PI / 2;  // Start at top
            var endAngle = startAngle + (splashWindow.progressValue / 100) * 2 * Math.PI;

            // Background circle
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI, false);
            ctx.lineWidth = 10;
            ctx.strokeStyle = "#44475a";  // Track color
            ctx.stroke();

            // Progress arc (aligned with qdarktheme progress bar color)
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, startAngle, endAngle, false);
            ctx.lineWidth = 10;
            ctx.strokeStyle = "#669ff5";  // Changed to match qdarktheme progress bar
            ctx.stroke();
        }

        // Trigger repaint when progressValue changes
        Connections {
            target: splashWindow
            function onProgressValueChanged() {
                progressCircle.requestPaint();
            }
        }
    }

    // Percentage label
    Label {
        id: percentageLabel
        text: "Loading News Publishing dash: " + Math.round(splashWindow.progressValue) + "%"
        color: "#f8f8f2"  // Text color from qdarktheme
        font.pixelSize: 20
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: progressCircle.bottom
        anchors.topMargin: 20  // Increased margin to ensure visibility
        visible: true  // Explicitly set visible
    }
}