// * Runs — the robovac runs going now, read from the log the robovac hooks write
// * (skills/robovac/scripts/runs.py). Methods: runsLog, turnEnded, runViews

import Foundation


//a run is a stretch its robot sweeps, while its agent's turn or its background work goes on; one
//heard nothing from in twelve hours is over, so a crashed session's robot still goes home...
let staleAfter: TimeInterval = 12 * 3600

//the log the hooks append to, or the one ROBOVAC_RUNS names...
func runsLog() -> URL {
    if let path = ProcessInfo.processInfo.environment["ROBOVAC_RUNS"] {
        return URL(fileURLWithPath: path)
    }
    return FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent(".claude/robovac/runs.jsonl")
}

//a run that stopped shows its ! this long before its suite may leave; the page is sent it with
//each run and holds the suite that long, so the hold has this one owner...
let showStopFor: TimeInterval = 10 * 60

//what the page is told about each run: its session, its own one line, whether its agent is
//working or stopped, why and when it stopped, and how long a stop holds its suite...
struct RunView: Equatable {
    let id: String
    let start: Double
    let say: String
    let state: String
    let why: String
    let at: Double

    var json: [String: Any] {
        ["id": id, "start": start, "say": say, "state": state, "why": why, "at": at,
         "hold": showStopFor]
    }
}


// ── a turn's end ──────────────────────────────────────────────────────────

//Claude Code runs no hook for Esc but writes a user line reading "[Request interrupted by user]",
//and an Esc between a turn's last reply and its Stop hook can run no hook and write no line; a
//transcript is read again only when it changes...
let escMark = "[Request interrupted by user"
var transcriptSeen: [String: (stamp: Date, esc: Double?, reply: Double?)] = [:]

//a reply that ended its turn ends it this long after, when no Stop hook has: that hook starts
//within a tenth of a second and is killed at five, as runs.py's REPLIED says...
let replyEnds: TimeInterval = 6

//a line's stamp, with fractions of a second as Claude Code writes it or in whole seconds, as
//runs.py reads both; one that will not parse, or none, is the transcript's modification time...
let stampFine: ISO8601DateFormatter = {
    let f = ISO8601DateFormatter()
    f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    return f
}()
let stampWhole = ISO8601DateFormatter()

//when a turn ended past `mark`, its transcript's length when the run began, with no hook to say
//so: at its first Esc, at once, or at the main agent's last assistant line, a subagent's skipped,
//once that line is `replyEnds` seconds old, if its message ended its turn; the Esc's words quoted
//in a tool result or mid-message are not an Esc, and a turn thinking or in a tool writes nothing,
//so is never ended...
func turnEnded(_ path: String, mark: Int, now: Double) -> Double? {
    let url = URL(fileURLWithPath: path)
    guard let stamp = (try? url.resourceValues(forKeys: [.contentModificationDateKey]))?
        .contentModificationDate else { return nil }
    let key = "\(path)#\(mark)"
    let seen: (stamp: Date, esc: Double?, reply: Double?)
    if let known = transcriptSeen[key], known.stamp == stamp {
        seen = known
    } else {
        seen = readTurn(url, mark: mark, stamp: stamp)
        transcriptSeen[key] = seen
    }
    if let esc = seen.esc {
        return esc
    }
    return seen.reply.flatMap { now - $0 >= replyEnds ? $0 : nil }
}

//one read of a transcript past `mark`, within its last 256 KB: its first Esc's time, and the time
//of the main agent's last assistant line if that line's message ended its turn...
func readTurn(_ url: URL, mark: Int, stamp: Date) -> (stamp: Date, esc: Double?, reply: Double?) {
    guard let file = try? FileHandle(forReadingFrom: url) else { return (stamp, nil, nil) }
    let size = (try? file.seekToEnd()) ?? 0
    try? file.seek(toOffset: max(UInt64(mark), size > 262144 ? size - 262144 : 0))
    let tail = String(decoding: (try? file.readToEnd()) ?? Data(), as: UTF8.self)
    try? file.close()
    let when = { (row: [String: Any]) -> Double in
        (row["timestamp"] as? String).flatMap {
            stampFine.date(from: $0) ?? stampWhole.date(from: $0)
        }?.timeIntervalSince1970 ?? stamp.timeIntervalSince1970
    }
    var esc: Double? = nil
    var reply: Double? = nil
    for line in tail.split(separator: "\n") {
        let isEsc = line.contains(escMark)
        guard isEsc || line.contains("\"assistant\""),
              let row = try? JSONSerialization.jsonObject(with: Data(line.utf8)) as? [String: Any],
              let message = row["message"] as? [String: Any] else { continue }
        if isEsc, esc == nil, row["type"] as? String == "user" {
            let parts = (message["content"] as? String).map { [$0] }
                ?? ((message["content"] as? [[String: Any]]) ?? []).compactMap { $0["text"] as? String }
            if parts.contains(where: { $0.hasPrefix(escMark) }) {
                esc = when(row)
            }
        }
        if row["type"] as? String == "assistant", row["isSidechain"] as? Bool != true {
            reply = message["stop_reason"] as? String == "end_turn" ? when(row) : nil
        }
    }
    return (stamp, esc, reply)
}


// ── the runs ──────────────────────────────────────────────────────────────

//the runs to show, oldest first: those whose agents are working, and those that stopped a little
//while ago (a finished turn, a wait on the person, Esc, an error, a closed session, or silence)...
func runViews(_ text: String, now: TimeInterval,
              ended: (String, Int, Double) -> Double? = turnEnded) -> [RunView] {
    var open: [String: (start: Double, heard: Double, say: String, transcript: String, mark: Int)] = [:]
    var stopped: [String: (start: Double, at: Double, say: String, why: String, transcript: String,
                           mark: Int)] = [:]

    //each session's turn and background work, folded as runs.py's doing folds them: a start opens
    //the turn with the tasks it carries, a work row says both, an end other than a wait closes both...
    var work: [String: (turn: Bool, tasks: [String: String])] = [:]
    for line in text.split(separator: "\n") {
        guard let data = line.data(using: .utf8),
              let row = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let sid = row["session"] as? String,
              let event = row["event"] as? String,
              let t = (row["t"] as? NSNumber)?.doubleValue
        else { continue }
        switch event {
        case "start":
            open[sid] = (t, t, row["say"] as? String ?? "", row["transcript"] as? String ?? "",
                         (row["mark"] as? NSNumber)?.intValue ?? 0)
            stopped[sid] = nil
            work[sid] = (true, row["tasks"] as? [String: String] ?? [:])
        case "say":
            if let run = open[sid] {
                open[sid] = (run.start, t, row["text"] as? String ?? "", run.transcript, run.mark)
            }
        case "work":
            if let run = open[sid] {
                open[sid] = (run.start, t, run.say, run.transcript, run.mark)
            }
            work[sid] = (row["turn"] as? Bool ?? false, row["tasks"] as? [String: String] ?? [:])
        case "end":
            let why = row["why"] as? String ?? "stopped"
            if let run = open[sid] {
                stopped[sid] = (run.start, t, run.say, why, run.transcript, run.mark)
            } else if let run = stopped[sid], run.why == "waiting on you" {

                //a wait ends when its turn finishes, errs, is interrupted or closes; any other stop
                //stands, since a session's close is logged long after its last turn finished...
                stopped[sid] = (run.start, t, run.say, why, run.transcript, run.mark)
            }
            open[sid] = nil
            if why != "waiting on you" {
                work[sid] = (false, [:])
            }
        default:
            break
        }
    }

    //an open turn the transcript shows ended, by an Esc or a reply no Stop hook followed, which no
    //hook logs until the next one: it stops every background agent but no shell...
    func turnOver(_ sid: String, _ transcript: String, _ mark: Int) -> (at: Double, shell: Bool)? {
        let (turn, tasks) = work[sid] ?? (true, [:])
        guard turn, !transcript.isEmpty, let at = ended(transcript, mark, now) else { return nil }
        return (at, tasks.values.contains("shell"))
    }
    var out: [(Double, RunView)] = []
    let live = { (sid: String, start: Double, say: String) in
        out.append((start, RunView(id: sid, start: start, say: say, state: "live", why: "", at: 0)))
    }
    for (sid, run) in open {
        if let over = turnOver(sid, run.transcript, run.mark), !over.shell {
            stopped[sid] = (run.start, over.at, run.say, "interrupted", run.transcript, run.mark)
        } else if now - run.heard < staleAfter {
            live(sid, run.start, run.say)
        } else {
            stopped[sid] = (run.start, run.heard + staleAfter, run.say, "went quiet",
                            run.transcript, run.mark)
        }
    }
    for (sid, run) in stopped {

        //nor does an Esc at the prompt a run docked waiting on, in its open turn: it shows
        //interrupted from then, or goes out to a background shell still running...
        var (why, at) = (run.why, run.at)
        if why == "waiting on you", let over = turnOver(sid, run.transcript, run.mark) {
            if over.shell {
                live(sid, run.start, run.say)
                continue
            }
            (why, at) = ("interrupted", over.at)
        }
        if now - at < showStopFor {
            out.append((run.start, RunView(id: sid, start: run.start, say: run.say,
                                           state: "stopped", why: why, at: at)))
        }
    }
    return out.sorted { $0.0 < $1.0 }.map { $0.1 }
}
