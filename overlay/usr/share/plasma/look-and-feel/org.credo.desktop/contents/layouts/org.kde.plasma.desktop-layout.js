// Credo OS default desktop, laid out like macOS 26:
//   top:     glass menu bar - Credo logo (opens the Credo menu), the active
//            app's menus, liturgical day, tray, clock
//   bottom:  Credo Dock (glass pill with magnification) in a transparent floating panel
//   desktop: "Today", "Holy Rosary" and "Roman Clock" widgets (drag to move)
// credo-theme rebuilds or adjusts this later (Credo Center -> Appearance -> Layout).

var bar = new Panel;
bar.location = "top";
bar.height = 32;                                   // like the macOS menu bar
try { bar.floating = false; } catch (e) {}
try { bar.opacity = "translucent"; } catch (e) {}

bar.addWidget("org.credo.menu");      // the Credo menu (like the Apple menu)
bar.addWidget("org.credo.appname");   // the active app's name in bold

bar.addWidget("org.kde.plasma.appmenu");
bar.addWidget("org.kde.plasma.panelspacer");
bar.addWidget("org.credo.liturgicalday");
bar.addWidget("org.kde.plasma.systemtray");
var clock = bar.addWidget("org.kde.plasma.digitalclock");
clock.currentConfigGroup = ["Appearance"];
clock.writeConfig("showDate", "true");
clock.writeConfig("dateFormat", "custom");
clock.writeConfig("customDateFormat", "ddd d MMM");
clock.writeConfig("dateDisplayFormat", 1);
// The date and time in the menu font (Inter, menu size), like macOS, not Plasma's large auto size.
clock.writeConfig("autoFontAndSize", "false");
clock.writeConfig("fontFamily", "Inter");
clock.writeConfig("fontSize", 10);
clock.writeConfig("fontWeight", 500);
clock.writeConfig("boldText", "false");

// ---- dock: transparent floating panel with the Credo Dock widget (glass pill, magnification)
var dock = new Panel;
dock.location = "bottom";
dock.height = 80;
try { dock.floating = true; } catch (e) {}
try { dock.lengthMode = "fit"; } catch (e) {}
try { dock.alignment = "center"; } catch (e) {}
dock.addWidget("org.credo.dock");
var desktops = desktopsForActivity(currentActivity());
for (var i = 0; i < desktops.length; i++) {
    var d = desktops[i];
    d.wallpaperPlugin = "org.kde.image";
    d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    d.writeConfig("Image", "file:///usr/share/wallpapers/Credo/contents/images/2880x1800.png");
    if (i == 0) {
        var sg = screenGeometry(d.screen), wy = sg.height - 330;
        d.addWidget("org.credo.today", 40, wy, 300, 170);
        d.addWidget("org.credo.rosary", 372, wy, 170, 170);
        d.addWidget("org.credo.clock", 590, wy, 170, 170);
    }
}
