// * test_runs — checks mac/Runs.swift: every stop shows, with why and when, for the ten minutes the
// * page is sent as each run's hold (R9, R19); an end after a wait takes the wait's place, and an
// * end after any other stop, such as a session's close, does not; an Esc in the transcript docks a
// * working run at the first one, and turns a run docked waiting on a prompt into an interrupted
// * one, and quoted words do not; twelve hours of silence docks it, a say row counting as heard
// * (R20, R21). R23 to R27 hold the turn and the background work: a turn closed with background
// * work going on stays out and is never read for its end, a reply that ended its turn with no Stop
// * docks it six seconds on, and an Esc leaves it out while a background shell runs; R28 counts a
// * work row as hearing from the run. R18 reads
// * skills/robovac/tests/esc_lines.json, whose lines runs.py's tests read too, so the two readers
// * give each line one time. Run tests/test_runs.sh, which builds this beside Runs.swift and passes
// * it that file; it exits 1 on a FAIL.

import Foundation
let now = 100_000.0
let dir = FileManager.default.temporaryDirectory.appendingPathComponent("runs-check-\(getpid())")
try! FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
func transcript(_ name: String, _ lines: [[String: Any]]) -> (String, Int) {
    let url = dir.appendingPathComponent(name)
    let text = lines.map { String(data: try! JSONSerialization.data(withJSONObject: $0), encoding: .utf8)! }
        .joined(separator: "\n") + "\n"
    try! text.write(to: url, atomically: true, encoding: .utf8)
    return (url.path, text.utf8.count)
}
func user(_ text: String, at stamp: String = "1970-01-02T03:46:00.000Z") -> [String: Any] {
    ["type": "user", "timestamp": stamp,
     "message": ["role": "user", "content": [["type": "text", "text": text]]]]
}
func result(_ text: String) -> [String: Any] {
    ["type": "user", "message": ["role": "user", "content": [["type": "tool_result", "content": text]]]]
}
let esc = "[Request interrupted by user]"
let (early, earlyMark) = transcript("early.jsonl", [user(esc), user("/robovac")])
let (pressed, _) = transcript("pressed.jsonl", [user("/robovac"), user(esc)])
let (quoted, _) = transcript("quoted.jsonl", [user("/robovac"), result("ESC = '\(esc)'"),
                                              user("why does it say \(esc)?"),
                                              ["type": "assistant", "message": ["role": "assistant",
                                               "content": [["type": "text", "text": esc]]]]])
let (plain, _) = transcript("plain.jsonl", [user("/robovac"),
                                            ["type": "user", "message": ["role": "user", "content": esc]]])
let (cached, _) = transcript("cached.jsonl", [user("/robovac")])
let (waiting, _) = transcript("waiting.jsonl", [user("/robovac")])
let (twice, _) = transcript("twice.jsonl", [user("/robovac"), user(esc, at: "1970-01-02T03:45:00.000Z"),
                                            user(esc)])
func row(_ s: String, _ e: String, _ t: Double, _ extra: String = "") -> String {
    "{\"session\": \"\(s)\", \"event\": \"\(e)\", \"t\": \(t)\(extra)}"
}
let log = [
    row("live", "start", now - 60),
    row("quiet", "start", now - staleAfter - 120),
    row("done", "start", now - 500), row("done", "end", now - 200, ", \"why\": \"finished\""),
    row("err", "start", now - 500), row("err", "end", now - 100, ", \"why\": \"error: x\""),
    row("old", "start", now - 3000), row("old", "end", now - 2000, ", \"why\": \"finished\""),
    row("early", "start", now - 50, ", \"transcript\": \"\(early)\", \"mark\": \(earlyMark)"),
    row("pressed", "start", now - 50, ", \"transcript\": \"\(pressed)\", \"mark\": 10"),
    row("quoted", "start", now - 50, ", \"transcript\": \"\(quoted)\", \"mark\": 10"),
    row("plain", "start", now - 50, ", \"transcript\": \"\(plain)\", \"mark\": 10"),
    row("twice", "start", now - 500, ", \"transcript\": \"\(twice)\", \"mark\": 10"),
    row("resumed", "start", now - 30, ", \"via\": \"again\", \"say\": \"binning leftovers\""),
    row("waited", "start", now - 400), row("waited", "ask", now - 390, ", \"id\": \"a1\""),
    row("waited", "end", now - 380, ", \"why\": \"waiting on you\""),
    row("waited", "answered", now - 300, ", \"ask\": \"a1\""),
    row("waited", "end", now - 250, ", \"why\": \"finished\""),
    row("gone", "start", now - 4000), row("gone", "end", now - 3500, ", \"why\": \"finished\""),
    row("gone", "end", now - 30, ", \"why\": \"session closed\""),
    row("closed", "start", now - 400), row("closed", "end", now - 380, ", \"why\": \"waiting on you\""),
    row("closed", "end", now - 30, ", \"why\": \"session closed\""),
    row("kept", "start", now - 400), row("kept", "end", now - 100, ", \"why\": \"finished\""),
    row("kept", "end", now - 30, ", \"why\": \"session closed\""),
    row("both", "start", now - 400), row("both", "end", now - 380, ", \"why\": \"waiting on you\""),
    row("both", "end", now - 250, ", \"why\": \"finished\""), row("both", "end", now - 30, ", \"why\": \"session closed\""),
    row("waitesc", "start", now - 60, ", \"transcript\": \"\(pressed)\", \"mark\": 10"),
    row("waitesc", "end", now - 45, ", \"why\": \"waiting on you\""),
    row("waitplain", "start", now - 60, ", \"transcript\": \"\(waiting)\", \"mark\": 10"),
    row("waitplain", "end", now - 45, ", \"why\": \"waiting on you\""),
    row("waitearly", "start", now - 60, ", \"transcript\": \"\(early)\", \"mark\": \(earlyMark)"),
    row("waitearly", "end", now - 45, ", \"why\": \"waiting on you\""),
    row("doneesc", "start", now - 60, ", \"transcript\": \"\(pressed)\", \"mark\": 10"),
    row("doneesc", "end", now - 45, ", \"why\": \"finished\""),
    row("ten", "start", now - 700), row("ten", "end", now - 590, ", \"why\": \"finished\""),
    row("eleven", "start", now - 700), row("eleven", "end", now - 610, ", \"why\": \"finished\""),
    row("said", "start", now - 46_800), row("said", "say", now - 3600, ", \"text\": \"binning leftovers\""),
    row("h11", "start", now - 43_140), row("h13", "start", now - 43_260),
].joined(separator: "\n")
var fails = 0
func check(_ name: String, _ ok: Bool, _ got: Any) {
    print((ok ? "PASS " : "FAIL ") + name + (ok ? "" : "  [\(got)]"))
    if !ok { fails += 1 }
}
let views = Dictionary(uniqueKeysWithValues: runViews(log, now: now).map { ($0.id, $0) })
check("R1 a working run is live", views["live"]?.state == "live" && views["live"]?.at == 0, views["live"] as Any)
check("R2 twelve silent hours stop a run when they ran out",
      views["quiet"]?.state == "stopped" && views["quiet"]?.why == "went quiet"
      && views["quiet"]?.at == now - 120, views["quiet"] as Any)
check("R3 a finished turn shows stopped, with when", views["done"]?.state == "stopped"
      && views["done"]?.why == "finished" && views["done"]?.at == now - 200, views["done"] as Any)
check("R4 an error shows stopped, with its why", views["err"]?.why == "error: x", views["err"] as Any)
check("R5 a stop past ten minutes is not shown", views["old"] == nil, views["old"] as Any)
check("R6 Esc before the run began does not stop it", views["early"]?.state == "live", views["early"] as Any)
check("R7 Esc after it began stops it as interrupted, at the Esc's time",
      views["pressed"]?.state == "stopped" && views["pressed"]?.why == "interrupted"
      && views["pressed"]?.at == 99960, views["pressed"] as Any)
check("R8 the mark quoted in a tool result, mid-message or by the agent does not stop it",
      views["quoted"]?.state == "live", views["quoted"] as Any)
check("R10 an Esc line with plain string content stops it", views["plain"]?.why == "interrupted",
      views["plain"] as Any)
check("R12 two Escs in one run stop it at the first, as the hooks log it",
      views["twice"]?.at == 99900, views["twice"] as Any)
check("R13 a run that goes on keeps the line its start carries", views["resumed"]?.say == "binning leftovers",
      views["resumed"] as Any)
check("R14 an end after a wait replaces its why and when, in one stopped view",
      runViews(log, now: now).filter { $0.id == "waited" }.count == 1 && views["waited"]?.state == "stopped"
      && views["waited"]?.why == "finished" && views["waited"]?.at == now - 250, views["waited"] as Any)
check("R15 a session closing long after its turn finished brings no stopped run back", views["gone"] == nil,
      views["gone"] as Any)
check("R16 a close ends a wait as closed, and leaves a finish, or a finish after a wait, as it was",
      views["closed"]?.why == "session closed" && views["closed"]?.at == now - 30
      && views["kept"]?.why == "finished" && views["kept"]?.at == now - 100
      && views["both"]?.why == "finished" && views["both"]?.at == now - 250,
      [views["closed"] as Any, views["kept"] as Any, views["both"] as Any])
check("R17 an Esc at a prompt that docked the run shows it interrupted, at the Esc's time; one before "
      + "the run began, or none, leaves the wait, and a finished run stays finished",
      views["waitesc"]?.why == "interrupted" && views["waitesc"]?.at == 99960
      && views["waitplain"]?.why == "waiting on you" && views["waitplain"]?.at == now - 45
      && views["waitearly"]?.why == "waiting on you"
      && views["doneesc"]?.why == "finished" && views["doneesc"]?.at == now - 45,
      [views["waitesc"] as Any, views["waitplain"] as Any, views["waitearly"] as Any, views["doneesc"] as Any])

//R11: a transcript whose modification date has not moved is not read again...
let url = URL(fileURLWithPath: cached)
let date = Date(timeIntervalSince1970: 1_700_000_000)
try! FileManager.default.setAttributes([.modificationDate: date], ofItemAtPath: cached)
let first = turnEnded(cached, mark: 10, now: now)
let more = "{\"type\": \"user\", \"message\": {\"role\": \"user\", \"content\": \"\(esc)\"}}\n"
let h = try! FileHandle(forWritingTo: url); h.seekToEndOfFile(); h.write(more.data(using: .utf8)!); h.closeFile()
try! FileManager.default.setAttributes([.modificationDate: date], ofItemAtPath: cached)
let unchanged = turnEnded(cached, mark: 10, now: now)
try! FileManager.default.setAttributes([.modificationDate: Date()], ofItemAtPath: cached)
let moved = turnEnded(cached, mark: 10, now: now)
check("R11 a transcript is read again only once it changes", first == nil && unchanged == nil && moved != nil,
      [first as Any, unchanged as Any, moved as Any])
check("R9 the page is told why and when, and the ten minutes a stop holds its suite",
      (views["done"]?.json["at"] as? Double) == now - 200 && (views["done"]?.json["why"] as? String) == "finished"
      && (views["done"]?.json["hold"] as? Double) == 600 && (views["live"]?.json["hold"] as? Double) == 600,
      views["done"]?.json as Any)
check("R19 a stop shows for ten minutes and no longer", views["ten"]?.why == "finished" && views["eleven"] == nil,
      [views["ten"] as Any, views["eleven"] as Any])
check("R20 a run's say row gives it its line and counts as hearing from it",
      views["said"]?.state == "live" && views["said"]?.say == "binning leftovers", views["said"] as Any)
check("R21 a run goes quiet at twelve hours unheard, not before", views["h11"]?.state == "live"
      && views["h13"]?.why == "went quiet" && views["h13"]?.at == now - 60, [views["h11"] as Any, views["h13"] as Any])

//R23 to R27: the turn and the background work, in a log of their own, read at two times...
func answer(_ text: String, at stamp: String, stop: String = "end_turn") -> [String: Any] {
    ["type": "assistant", "timestamp": stamp,
     "message": ["role": "assistant", "stop_reason": stop, "content": [["type": "text", "text": text]]]]
}
let (replied, _) = transcript("replied.jsonl", [user("/robovac"), answer("done", at: "1970-01-02T03:46:00.000Z")])
func work(_ s: String, _ t: Double, turn: Bool, _ tasks: String) -> String {
    "{\"session\": \"\(s)\", \"event\": \"work\", \"t\": \(t), \"turn\": \(turn), \"tasks\": {\(tasks)}}"
}
let shellTask = "\"s1\": \"shell\""
let agentTask = "\"ag1\": \"subagent\""
let worked = [
    row("bg", "start", now - 300, ", \"transcript\": \"\(replied)\", \"mark\": 10"),
    work("bg", now - 200, turn: false, shellTask),
    row("noreply", "start", now - 300, ", \"transcript\": \"\(replied)\", \"mark\": 10"),
    row("escshell", "start", now - 300, ", \"transcript\": \"\(pressed)\", \"mark\": 10"),
    work("escshell", now - 250, turn: true, shellTask + ", " + agentTask),
    row("escagent", "start", now - 300, ", \"transcript\": \"\(pressed)\", \"mark\": 10"),
    work("escagent", now - 250, turn: true, agentTask),
    row("waitshell", "start", now - 300, ", \"transcript\": \"\(pressed)\", \"mark\": 10"),
    work("waitshell", now - 250, turn: true, shellTask),
    row("waitshell", "end", now - 45, ", \"why\": \"waiting on you\""),
    row("waitclosed", "start", now - 300, ", \"transcript\": \"\(pressed)\", \"mark\": 10"),
    work("waitclosed", now - 250, turn: false, agentTask),
    row("waitclosed", "end", now - 45, ", \"why\": \"waiting on you\""),
    row("heardwork", "start", now - 46_800), work("heardwork", now - 39_600, turn: false, shellTask),
].joined(separator: "\n")
let late = Dictionary(uniqueKeysWithValues: runViews(worked, now: now).map { ($0.id, $0) })
let soon = Dictionary(uniqueKeysWithValues: runViews(worked, now: 99_965).map { ($0.id, $0) })
check("R23 a turn closed with a background shell running stays live, and its last reply ends nothing",
      late["bg"]?.state == "live", late["bg"] as Any)
check("R24 a turn whose last reply ended it with no Stop stays live under six seconds, then stops "
      + "interrupted at the reply", soon["noreply"]?.state == "live"
      && late["noreply"]?.state == "stopped" && late["noreply"]?.why == "interrupted"
      && late["noreply"]?.at == 99960, [soon["noreply"] as Any, late["noreply"] as Any])
check("R25 an Esc leaves the run live while a background shell runs, and stops it when only an agent "
      + "did, since the Esc stops the agent", late["escshell"]?.state == "live"
      && late["escagent"]?.state == "stopped" && late["escagent"]?.why == "interrupted",
      [late["escshell"] as Any, late["escagent"] as Any])
check("R26 an Esc at a wait in an open turn sends the run live while a background shell runs",
      late["waitshell"]?.state == "live", late["waitshell"] as Any)
check("R27 a wait after the turn closed is not read for an Esc in the main transcript",
      late["waitclosed"]?.state == "stopped" && late["waitclosed"]?.why == "waiting on you",
      late["waitclosed"] as Any)
check("R28 a work row counts as hearing from a run, so background work silent under twelve hours "
      + "keeps it live", late["heardwork"]?.state == "live", late["heardwork"] as Any)

//R18: each line in the file runs.py's own test reads gets the time that file names...
let fixture = URL(fileURLWithPath: CommandLine.arguments[1])
let shared = try! JSONSerialization.jsonObject(with: Data(contentsOf: fixture)) as! [String: Any]
for (n, item) in (shared["cases"] as! [[String: Any]]).enumerated() {
    let lines = (item["lines"] as! [String]).map { $0 + "\n" }
    let pad = item["pad"] as! Int
    let file = dir.appendingPathComponent("shared-\(n).jsonl")
    try! (lines.joined() + (pad > 0 ? String(repeating: "x", count: pad) + "\n" : ""))
        .write(to: file, atomically: true, encoding: .utf8)
    var want = item["at"] as? Double
    if item["at"] as? String == "mtime" {
        try! FileManager.default.setAttributes([.modificationDate: Date(timeIntervalSince1970: 1_700_000_000)],
                                               ofItemAtPath: file.path)
        want = 1_700_000_000
    }
    let at = (item["now"] as? Double) ?? Date().timeIntervalSince1970
    let got = turnEnded(file.path, mark: lines.prefix(item["mark"] as! Int).joined().utf8.count, now: at)
    check("R18 \(item["name"] as! String)", got == want, got as Any)
}
try? FileManager.default.removeItem(at: dir)
exit(fails == 0 ? 0 : 1)
