// * Robovac — the app's window: a glass window with the house page inside, its Dock icon and
// * its menus. Closing the window quits.

import Cocoa
import WebKit



// ── the parts of the window ───────────────────────────────────────────────

//a strip along the top edge, under the window buttons, acts as the title bar: a drag moves the
//window, a double click does what the person set for title bars, and scrolling still zooms...
final class DragStrip: NSView {
    weak var house: NSView?

    override func mouseDown(with event: NSEvent) {
        guard event.clickCount == 2 else {
            window?.performDrag(with: event)
            return
        }
        switch UserDefaults.standard.string(forKey: "AppleActionOnDoubleClick") ?? "Maximize" {
        case "Minimize":
            window?.performMiniaturize(nil)
        case "None":
            break

        //Fill, macOS 15's choice, has no public call; Chromium, iTerm2, Zed and Firefox send this one...
        case "Fill" where window?.responds(to: Selector(("_zoomFill:"))) == true:
            window?.perform(Selector(("_zoomFill:")), with: nil)
        default:
            window?.performZoom(nil)
        }
    }

    override func scrollWheel(with event: NSEvent) {
        house?.scrollWheel(with: event)
    }
}

//the house page; held ⌘ turns any drag on it into moving the window, and its context menu is
//the house's own...
final class HouseView: WKWebView {
    var controls: NSMenu?

    //WebKit's menu, opened by a right click, a control click, the keyboard or VoiceOver, is
    //emptied and given copies of the house's items, since an item can sit in one menu only...
    override func willOpenMenu(_ menu: NSMenu, with event: NSEvent) {
        menu.removeAllItems()
        for item in controls?.items ?? [] {
            menu.addItem(item.copy() as! NSMenuItem)
        }
    }

    override func mouseDown(with event: NSEvent) {
        if event.modifierFlags.contains(.command) {
            window?.performDrag(with: event)
            return
        }
        super.mouseDown(with: event)
    }

    override var mouseDownCanMoveWindow: Bool { false }
}


// ── the app ───────────────────────────────────────────────────────────────

final class AppDelegate: NSObject, NSApplicationDelegate, WKScriptMessageHandler,
                         WKNavigationDelegate {
    var window: NSWindow!
    var web: HouseView!
    var shown: [RunView] = []
    var logRead: (stamp: Date, text: String)?

    func applicationDidFinishLaunching(_ notification: Notification) {
        let frame = NSRect(x: 0, y: 0, width: 560, height: 420)
        window = NSWindow(contentRect: frame,
                          styleMask: [.titled, .closable, .miniaturizable, .resizable,
                                      .fullSizeContentView],
                          backing: .buffered, defer: false)
        window.title = "Robovac"
        window.titleVisibility = .hidden
        window.titlebarAppearsTransparent = true
        window.isOpaque = false
        window.backgroundColor = .clear
        window.isMovableByWindowBackground = false
        window.minSize = NSSize(width: 300, height: 220)

        //the frame is kept by its autosave name, so macOS saves no window state to reopen...
        window.isRestorable = false

        //macOS's own glass, blurring whatever is behind the window...
        let glass = NSVisualEffectView(frame: frame)
        glass.material = .hudWindow
        glass.blendingMode = .behindWindow
        glass.state = .active
        glass.autoresizingMask = [.width, .height]
        window.contentView = glass

        //the runs going now are read before the page loads, and it is told them once it has...
        readRuns(send: false)
        let config = WKWebViewConfiguration()
        config.userContentController.add(self, name: "robovac")
        web = HouseView(frame: glass.bounds, configuration: config)
        web.autoresizingMask = [.width, .height]
        web.setValue(false, forKey: "drawsBackground")
        web.underPageBackgroundColor = .clear
        web.allowsMagnification = false
        web.navigationDelegate = self
        glass.addSubview(web)

        let strip = DragStrip(frame: NSRect(x: 0, y: frame.height - 28, width: frame.width, height: 28))
        strip.autoresizingMask = [.width, .minYMargin]
        strip.house = web
        glass.addSubview(strip)

        let page = Bundle.main.resourceURL!.appendingPathComponent("app")
        var index = URLComponents(url: page.appendingPathComponent("index.html"),
                                  resolvingAgainstBaseURL: true)!
        let env = ProcessInfo.processInfo.environment
        var query: [String] = []

        //a recording can name the house it films, by its seed...
        if let seed = env["ROBOVAC_HOUSE"], Int(seed) != nil {
            query.append("house=\(seed)")
        }
        index.query = query.isEmpty ? nil : query.joined(separator: "&")
        web.loadFileURL(index.url!, allowingReadAccessTo: page)

        window.setFrameAutosaveName("RobovacWindow")
        if !window.setFrameUsingName("RobovacWindow") {
            window.center()
        }
        buildMenus()

        //the window shows once the page has drawn, or after a second and a half if it is slow...
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { [weak self] in
            self?.present()
        }
        playKeys()
        Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in
            self?.readRuns()
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    func present() {
        guard !window.isVisible else { return }
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }


    // ── the runs going now ─────────────────────────────────────────────────

    //the log is read again only when it changes; the runs going are worked out every time, so a
    //silent one still runs out of time...
    func readRuns(send: Bool = true) {
        let url = runsLog()
        let stamp = (try? url.resourceValues(forKeys: [.contentModificationDateKey]))?
            .contentModificationDate ?? .distantPast
        if logRead?.stamp != stamp {
            logRead = (stamp, (try? String(contentsOf: url, encoding: .utf8)) ?? "")
        }
        let now = runViews(logRead?.text ?? "", now: Date().timeIntervalSince1970)
        if now != shown {
            shown = now
            if send {
                sendRuns()
            }
        }
    }

    func sendRuns() {
        guard let data = try? JSONSerialization.data(withJSONObject: shown.map { $0.json }),
              let ids = String(data: data, encoding: .utf8) else { return }
        run("robovac.sync(\(ids))")
    }

    //a page that has just loaded is told the runs going, and the window shows...
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        sendRuns()
        present()
    }

    //the page sends nothing back; the handler is registered so the page knows it is in the app...
    func userContentController(_ c: WKUserContentController, didReceive message: WKScriptMessage) {}

    func run(_ js: String) {
        web.evaluateJavaScript(js, completionHandler: nil)
    }


    // ── the menus ──────────────────────────────────────────────────────────

    //the app menu, View with fitting the house, and Window; the house's right-click menu holds
    //the fit and quit as well...
    func buildMenus() {
        let bar = NSMenu()
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "About Robovac",
                        action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)),
                        keyEquivalent: "")
        appMenu.addItem(.separator())
        let services = NSMenu(title: "Services")
        appMenu.addItem(withTitle: "Services", action: nil, keyEquivalent: "").submenu = services
        NSApp.servicesMenu = services
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Hide Robovac", action: #selector(NSApplication.hide(_:)),
                        keyEquivalent: "h")
        appMenu.addItem(withTitle: "Hide Others",
                        action: #selector(NSApplication.hideOtherApplications(_:)),
                        keyEquivalent: "h").keyEquivalentModifierMask = [.command, .option]
        appMenu.addItem(withTitle: "Show All",
                        action: #selector(NSApplication.unhideAllApplications(_:)),
                        keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quit Robovac", action: #selector(NSApplication.terminate(_:)),
                        keyEquivalent: "q")
        let viewMenu = NSMenu(title: "View")
        let fitItem = viewMenu.addItem(withTitle: "Fit the House", action: #selector(fit),
                                       keyEquivalent: "0")
        fitItem.target = self
        let fileMenu = NSMenu(title: "File")
        fileMenu.addItem(withTitle: "Close", action: #selector(NSWindow.performClose(_:)),
                         keyEquivalent: "w")
        let windowMenu = NSMenu(title: "Window")
        windowMenu.addItem(withTitle: "Minimize", action: #selector(NSWindow.performMiniaturize(_:)),
                           keyEquivalent: "m")
        windowMenu.addItem(withTitle: "Zoom", action: #selector(NSWindow.performZoom(_:)),
                           keyEquivalent: "")
        windowMenu.addItem(.separator())
        windowMenu.addItem(withTitle: "Bring All to Front",
                           action: #selector(NSApplication.arrangeInFront(_:)), keyEquivalent: "")
        for menu in [appMenu, fileMenu, viewMenu, windowMenu] {
            bar.addItem(withTitle: "", action: nil, keyEquivalent: "").submenu = menu
        }
        NSApp.mainMenu = bar
        NSApp.windowsMenu = windowMenu

        let controls = NSMenu()
        controls.addItem(withTitle: "Fit the House", action: #selector(fit), keyEquivalent: "")
            .target = self
        controls.addItem(.separator())
        controls.addItem(withTitle: "Quit Robovac", action: #selector(NSApplication.terminate(_:)),
                         keyEquivalent: "")
        web.controls = controls
    }

    @objc func fit() {
        run("robovac.fit()")
    }

    //when ROBOVAC_KEYS is set, as "seconds:key,…", each key is pressed on the page that long after
    //launch, so a recording can drive the camera without anyone at the keyboard...
    func playKeys() {
        guard let spec = ProcessInfo.processInfo.environment["ROBOVAC_KEYS"] else { return }
        for part in spec.split(separator: ",") {
            let bits = part.split(separator: ":", maxSplits: 1)
            guard bits.count == 2, let at = Double(bits[0]),
                  bits[1].allSatisfy({ $0.isLetter || $0.isNumber }) else { continue }
            let key = String(bits[1])
            DispatchQueue.main.asyncAfter(deadline: .now() + at) {
                self.run("window.dispatchEvent(new KeyboardEvent('keydown', {key: '\(key)'}))")
            }
        }
    }
}


@main
enum Robovac {
    static let delegate = AppDelegate()

    static func main() {
        let app = NSApplication.shared
        app.delegate = delegate
        app.setActivationPolicy(.regular)
        app.run()
    }
}
