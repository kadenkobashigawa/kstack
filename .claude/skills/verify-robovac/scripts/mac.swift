// * mac — what verify.py asks of macOS that has no command of its own: a process's window, bringing
// * it to the front, the Screen Recording grant, and the Trash. common.py compiles it once per run.
// * Methods: window, front, preflight, trash

import AppKit
import CoreGraphics



// ── the commands ──────────────────────────────────────────────────────────

//the on-screen, normal-layer window of one process, as "id x y width height" in points from the
//main display's top left, the frame `screencapture -R` takes; nothing when it has none...
func window(_ pid: Int) {
    let info = CGWindowListCopyWindowInfo([.optionOnScreenOnly], kCGNullWindowID)
    let list = info as? [[String: Any]] ?? []
    for w in list where (w[kCGWindowOwnerPID as String] as? Int) == pid
        && (w[kCGWindowLayer as String] as? Int) == 0 {
        guard let id = w[kCGWindowNumber as String] as? Int,
              let b = w[kCGWindowBounds as String] as? [String: Double] else { continue }
        print(id, Int(b["X"]!), Int(b["Y"]!), Int(b["Width"]!), Int(b["Height"]!))
        return
    }
}

//brings one running app to the front, as a click on its Dock icon does; exit 1 when it is gone...
func front(_ pid: Int) -> Int32 {
    guard let app = NSRunningApplication(processIdentifier: pid_t(pid)) else { return 1 }
    return app.activate(options: [.activateAllWindows]) ? 0 : 1
}

//whether this process may record the screen, asked without prompting...
func preflight() {
    print(CGPreflightScreenCaptureAccess() ? "yes" : "no")
}

//moves each path to the Trash the way Finder does, printing where it went...
func trash(_ paths: [String]) -> Int32 {
    var failed: Int32 = 0
    for path in paths {
        var landed: NSURL?
        do {
            try FileManager.default.trashItem(at: URL(fileURLWithPath: path),
                                              resultingItemURL: &landed)
            print(landed?.path ?? path)
        } catch {
            FileHandle.standardError.write(Data("mac: could not trash \(path): \(error)\n".utf8))
            failed = 1
        }
    }
    return failed
}


// ── main ──────────────────────────────────────────────────────────────────

let args = CommandLine.arguments
switch (args.count > 1 ? args[1] : "", args.count > 2 ? Int(args[2]) : nil) {
case ("window", let pid?):
    window(pid)
case ("front", let pid?):
    exit(front(pid))
case ("preflight", _):
    preflight()
case ("trash", _) where args.count > 2:
    exit(trash(Array(args[2...])))
default:
    let usage = "usage: mac window <pid> | front <pid> | preflight | trash <path>...\n"
    FileHandle.standardError.write(Data(usage.utf8))
    exit(2)
}
