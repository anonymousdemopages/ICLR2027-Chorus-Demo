#!/usr/bin/env python3
"""Render the Chorus demo page from a gathered bundle.

Usage:
    python3 build_demo.py --bundle /path/to/bundle [--sssd-recordings]

Reads bundle/manifest.json, copies only the referenced audio into ./audio,
and writes ./index.html. Standard library only.
"""
import argparse
import html
import json
import shutil
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent

CH_COLORS = ["#2a6fdb", "#2bb673", "#f28c28", "#b04ddb"]
CH_NAMES = ["A", "B", "C", "D"]

TITLE = "Chorus: Multi-Speaker Conversational Speech Generation with Communicating Single-Speaker TTS Models"

CSS = """
:root{--ink:#1c1f24;--muted:#5c6470;--line:#e3e6ea;--bg:#fbfbfc;--card:#ffffff;--accent:#2a6fdb;--hl:rgba(255,196,0,.35)}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
main{max-width:1120px;margin:0 auto;padding:24px 20px 80px}
h1{font-size:26px;line-height:1.25;margin:8px 0 6px}
h2{font-size:21px;margin:56px 0 8px;padding-top:14px;border-top:2px solid var(--ink)}
h3{font-size:16px;margin:26px 0 8px}
p{margin:6px 0 10px}
.sub{color:var(--muted);font-size:14px}
.lead{font-size:16px;max-width:900px}
.note{background:#f3f6fb;border-left:4px solid var(--accent);padding:10px 14px;border-radius:4px;margin:14px 0}
.fig{width:100%;height:auto;border:1px solid var(--line);border-radius:6px;background:#fff;margin:14px 0 6px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin:16px 0}
.card h3{margin-top:0}
.tx{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;font-size:14px;margin:6px 0 12px}
.tx b{white-space:nowrap}
.tx span{color:#2a2f36}
table.grid{width:100%;border-collapse:collapse}
table.grid td{padding:6px 8px;border-top:1px solid var(--line);vertical-align:middle}
table.grid td.sys{width:190px;font-weight:600}
table.grid td.sys small{display:block;font-weight:400;color:var(--muted)}
table.grid td.pl{width:330px}
audio{width:300px;height:34px;display:block}
.tabs{display:flex;gap:4px;margin:0 0 4px}
.tabs button{font:12px/1 inherit;padding:4px 8px;border:1px solid var(--line);background:#fff;border-radius:4px;cursor:pointer;color:var(--muted)}
.tabs button.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.tabs button.ch0{border-color:#2a6fdb}.tabs button.ch1{border-color:#2bb673}.tabs button.ch2{border-color:#f28c28}.tabs button.ch3{border-color:#b04ddb}
.strip{width:100%;display:block;cursor:pointer}
.strip rect.bg{fill:#f4f5f7}
.strip text{font-size:15px;fill:var(--muted);font-family:inherit}
.strip line.ph{stroke:#e0245e;stroke-width:1.5}
.badge{display:inline-block;font-size:12px;padding:2px 8px;border-radius:999px;background:#eef2f7;color:#2a2f36;margin-right:6px}
.badge.bc{background:#fff3cd}.badge.in{background:#f8d7da}.badge.ov{background:#d1ecf1}
.evbtn{font:13px inherit;padding:4px 10px;border:1px solid var(--ink);background:#fff;border-radius:4px;cursor:pointer;margin-top:4px}
details{margin:10px 0}
details summary{cursor:pointer;color:var(--muted);font-size:14px}
details ul{font-size:13.5px;color:#2a2f36}
.legend{font-size:13px;color:var(--muted);margin:4px 0 10px}
.legend i{display:inline-block;width:12px;height:12px;border-radius:2px;vertical-align:-2px;margin:0 4px 0 10px}
.kgroup{margin-top:22px}
footer{margin-top:60px;padding-top:14px;border-top:1px solid var(--line);color:var(--muted);font-size:13.5px}
@media (max-width:760px){table.grid td.pl{width:auto}audio{width:100%}table.grid td.sys{width:auto}.tx{grid-template-columns:1fr}}
"""

JS = """
(function(){
  // one player per cell; tabs swap the source and keep the position
  document.querySelectorAll('.tabs').forEach(function(t){
    var au = t.parentNode.querySelector('audio');
    t.querySelectorAll('button').forEach(function(b){
      b.addEventListener('click', function(){
        var pos = au.currentTime, playing = !au.paused;
        t.querySelectorAll('button').forEach(function(x){x.classList.remove('on')});
        b.classList.add('on');
        au.src = b.dataset.src; au.load();
        au.addEventListener('loadedmetadata', function h(){ au.currentTime = pos; if (playing) au.play(); au.removeEventListener('loadedmetadata', h); });
      });
    });
  });
  // strips: playhead follows the associated audio, click seeks
  document.querySelectorAll('svg.strip').forEach(function(s){
    var au = document.getElementById(s.dataset.audio); if(!au) return;
    var dur = parseFloat(s.dataset.dur), ph = s.querySelector('line.ph');
    var W = parseFloat(s.getAttribute('viewBox').split(' ')[2]);
    au.addEventListener('timeupdate', function(){ var x = 60 + (au.currentTime/dur)*(W-68); ph.setAttribute('x1',x); ph.setAttribute('x2',x); });
    s.addEventListener('click', function(ev){
      var r = s.getBoundingClientRect(); var fx = (ev.clientX - r.left)/r.width*W; var t = Math.max(0, Math.min(dur, (fx-60)/(W-68)*dur));
      if (au.readyState === 0) { au.addEventListener('loadedmetadata', function h(){ au.currentTime = t; au.play(); au.removeEventListener('loadedmetadata', h); }); au.load(); }
      else { au.currentTime = t; au.play(); }
    });
  });
  document.querySelectorAll('.evbtn').forEach(function(b){
    b.addEventListener('click', function(){
      var au = document.getElementById(b.dataset.audio), t = parseFloat(b.dataset.t);
      if (au.readyState === 0) { au.addEventListener('loadedmetadata', function h(){ au.currentTime = t; au.play(); au.removeEventListener('loadedmetadata', h); }); au.load(); }
      else { au.currentTime = t; au.play(); }
    });
  });
  // pause every other player when one starts
  var all = document.querySelectorAll('audio');
  all.forEach(function(a){ a.addEventListener('play', function(){ all.forEach(function(o){ if(o!==a) o.pause(); }); }); });
})();
"""


def esc(s):
    return html.escape(s or "", quote=True)


class Builder:
    def __init__(self, bundle, out, sssd_recordings):
        self.bundle = bundle
        self.out = out
        self.man = json.load(open(bundle / "manifest.json"))
        self.sssd_recordings = sssd_recordings
        self.copied = set()
        self.n_audio = 0

    # ---- assets
    def use(self, rel):
        """Copy one bundle audio file into the page folder; return its page path."""
        if rel not in self.copied:
            src = self.bundle / rel
            dst = self.out / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            self.copied.add(rel)
        return rel

    # ---- components
    def player(self, pid, mix, chs=None, labels=None):
        """Audio element with optional Mix / per-channel tabs."""
        self.n_audio += 1
        h = ['<div class="pl-wrap">']
        if chs:
            h.append('<div class="tabs">')
            h.append(f'<button class="on" data-src="{self.use(mix)}">Mix</button>')
            for k, c in enumerate(chs):
                lab = labels[k] if labels else f"Speaker {CH_NAMES[k]}"
                h.append(f'<button class="ch{k}" data-src="{self.use(c)}">{esc(lab)}</button>')
            h.append('</div>')
        h.append(f'<audio id="{pid}" controls preload="none" src="{self.use(mix)}"></audio>')
        h.append('</div>')
        return "".join(h)

    def strip(self, pid, dur, rows, highlight=None, height_per_row=20):
        """Inline SVG activity strip.

        rows: list of dicts {label, spans:[[s,e],...], color, style: 'fill'|'outline'|'hatch'}
        """
        W = 800
        pad_l, pad_r, pad_t = 60, 8, 4
        H = pad_t + len(rows) * height_per_row + 18
        inner = W - pad_l - pad_r
        x = lambda t: pad_l + (t / dur) * inner if dur > 0 else pad_l
        h = [f'<svg class="strip" viewBox="0 0 {W} {H}" data-audio="{pid}" data-dur="{dur:.3f}" role="img" aria-label="speech activity">']
        h.append('<defs>' + ''.join(f'<pattern id="hatch{k}" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="{c}" fill-opacity="0.18"/><line x1="0" y1="0" x2="0" y2="6" stroke="{c}" stroke-width="2"/></pattern>' for k, c in enumerate(CH_COLORS)) + '</defs>')
        h.append(f'<rect class="bg" x="{pad_l}" y="{pad_t}" width="{inner}" height="{len(rows)*height_per_row}" />')
        for i, r in enumerate(rows):
            y = pad_t + i * height_per_row
            h.append(f'<text x="{pad_l-6}" y="{y+height_per_row-4}" text-anchor="end">{esc(r["label"])}</text>')
            for s, e in r["spans"]:
                s, e = max(0.0, float(s)), min(dur, float(e))
                if e <= s:
                    continue
                st = r.get("style", "fill")
                if st == "fill":
                    h.append(f'<rect x="{x(s):.1f}" y="{y+2}" width="{max(1.0, x(e)-x(s)):.1f}" height="{height_per_row-4}" fill="{r["color"]}" rx="2"/>')
                elif st == "outline":
                    h.append(f'<rect x="{x(s):.1f}" y="{y+2}" width="{max(1.0, x(e)-x(s)):.1f}" height="{height_per_row-4}" fill="none" stroke="{r["color"]}" stroke-width="1.5" rx="2"/>')
                else:
                    k = CH_COLORS.index(r["color"]) if r["color"] in CH_COLORS else 0
                    h.append(f'<rect x="{x(s):.1f}" y="{y+2}" width="{max(1.0, x(e)-x(s)):.1f}" height="{height_per_row-4}" fill="url(#hatch{k})" rx="2"/>')
        if highlight:
            s, e = highlight
            h.append(f'<rect x="{x(s):.1f}" y="{pad_t}" width="{max(2.0, x(e)-x(s)):.1f}" height="{len(rows)*height_per_row}" fill="var(--hl)" stroke="#e0a800" stroke-width="1"/>')
        # time axis ticks
        step = 5 if dur <= 40 else 10
        t = 0
        while t <= dur:
            h.append(f'<line x1="{x(t):.1f}" y1="{pad_t+len(rows)*height_per_row}" x2="{x(t):.1f}" y2="{pad_t+len(rows)*height_per_row+3}" stroke="#aab" />')
            h.append(f'<text x="{x(t):.1f}" y="{H-1}" text-anchor="middle">{t}s</text>')
            t += step
        h.append(f'<line class="ph" x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t+len(rows)*height_per_row}" />')
        h.append('</svg>')
        return "".join(h)

    @staticmethod
    def rows_from_spans(spans, names=None, style="fill"):
        return [{"label": (names[k] if names else f"Spk {CH_NAMES[k]}"), "spans": ch, "color": CH_COLORS[k], "style": style}
                for k, ch in enumerate(spans)]

    @staticmethod
    def rows_from_layout(layout, K=2):
        by = [[] for _ in range(K)]
        for t in layout:
            by[t["channel"]].append([t["start"], t["end"]])
        return [{"label": f"Tgt {CH_NAMES[k]}", "spans": by[k], "color": "#6b7280", "style": "outline"} for k in range(K)]

    @staticmethod
    def transcript(texts, names=None):
        h = ['<div class="tx">']
        for k, t in enumerate(texts):
            nm = names[k] if names else f"Speaker {CH_NAMES[k]}"
            h.append(f'<b style="color:{CH_COLORS[k]}">{esc(nm)}</b><span>{esc(t)}</span>')
        h.append('</div>')
        return "".join(h)

    def rules(self, keys):
        R = self.man["meta"]["rules"]
        items = "".join(f"<li>{esc(R[k])}</li>" for k in keys if k in R)
        return f'<details><summary>How these samples were chosen</summary><ul>{items}</ul></details>'

    # ---- sections
    def sec_grid(self):
        S = self.man["sections"]["zv_grid"]
        h = ['<h2 id="two-speaker">1. Two-speaker conversation (ZipVoice-Dialog test set)</h2>']
        h.append('<p class="lead">Every system generates the same conversations from the same transcript and the same prompt recordings. Systems with one channel per speaker also have a per-channel view and an activity strip. The other systems generate a single-channel mixture only. This is the setting of Table 1 in the paper.</p>')
        h.append(self.legend())
        for i, it in enumerate(S["items"]):
            h.append(f'<div class="card"><h3>Conversation {i+1}</h3>')
            h.append(self.transcript(it["text"]))
            h.append('<table class="grid">')
            for sy in S["systems"]:
                e = it["systems"][sy["key"]]
                pid = f"g{i}_{sy['key']}"
                h.append(f'<tr><td class="sys">{esc("Ground truth" if sy["key"] == "gt" else sy["name"])}<small>{"one channel per speaker" if sy["stereo"] else "single-channel mixture"}</small></td>')
                h.append(f'<td class="pl">{self.player(pid, e["mix"], e.get("ch"))}</td>')
                if sy["stereo"]:
                    dur = self.dur_of(e)
                    h.append(f'<td>{self.strip(pid, dur, self.rows_from_spans(e["spans"]))}</td>')
                else:
                    h.append('<td class="sub">single-channel mixture</td>')
                h.append('</tr>')
            h.append('</table></div>')
        return "".join(h)

    def dur_of(self, e):
        """Strip length: the mixture's real duration from its wav header, so the playhead never runs off the strip."""
        try:
            with wave.open(str(self.bundle / e["mix"]), "rb") as w:
                return w.getnframes() / w.getframerate()
        except Exception:
            if "duration" in e:
                return float(e["duration"])
            return max((float(t) for ch in e["spans"] for _, t in ch), default=0.0) + 0.5

    def legend(self):
        return ('<div class="legend">Activity strips: <i style="background:#2a6fdb"></i>Speaker A <i style="background:#2bb673"></i>Speaker B '
                '<i style="background:#f28c28"></i>Speaker C <i style="background:#b04ddb"></i>Speaker D '
                '<i style="border:1.5px solid #6b7280;background:#fff"></i>given turn timestamps '
                '<i style="background:repeating-linear-gradient(45deg,#2a6fdb 0 2px,#dfe8f8 2px 5px)"></i>given channel (ground truth). '
                'Speech regions are computed per channel with the VAD of pyannote. Click a strip to play from that point. The red line follows playback.</div>')

    def sec_interaction(self):
        S = self.man["sections"]["interaction"]
        h = ['<h2 id="interaction">2. Speaker interaction (backchannels, interruptions and overlaps)</h2>']
        h.append('<p class="lead">Chorus generates one channel per speaker in turn-order mode, so the text input carries only the turn order and the model decides all timing, including every overlap. The clips below are Chorus outputs on the ZipVoice-Dialog test set. The events were found automatically with the event labeler of the turn-taking judge of Talking Turns, which uses the VAD of pyannote on each channel and a lexical backchannel detector. They were not picked by hand. The highlighted interval is the detected event. The ground truth of the same transcript is shown for reference. This is the setting of Tables 2 and 3 in the paper.</p>')
        h.append(self.legend())
        kinds = {"backchannel": ("bc", "Backchannel"), "interruption": ("in", "Interruption"), "overlap": ("ov", "Sustained overlap")}
        for i, it in enumerate(S["items"]):
            cls, name = kinds[it["kind"]]
            ev = it["event"]
            desc = ""
            if it["kind"] == "backchannel":
                desc = f'Speaker {CH_NAMES[it["channel"]]} says <i>{esc(it.get("event_text") or "")}</i> at {ev[0]:.1f} s during the turn of speaker {CH_NAMES[1-it["channel"]]} ({it["host"][0]:.1f} to {it["host"][1]:.1f} s).'
            elif it["kind"] == "interruption":
                desc = f'Speaker {CH_NAMES[it["channel"]]} starts at {ev[0]:.1f} s while speaker {CH_NAMES[1-it["channel"]]} is still talking (until {it["host"][1]:.1f} s) and keeps the turn for {it["score"]:.1f} s after that.'
            else:
                desc = f'Both speakers talk at once for {it["score"]:.1f} s ({ev[0]:.1f} to {ev[1]:.1f} s).'
            h.append(f'<div class="card"><h3><span class="badge {cls}">{name}</span> Conversation {i+1}</h3>')
            h.append(f'<p>{desc}</p>')
            h.append(self.transcript(it["text"]))
            h.append('<table class="grid">')
            c = it["chorus"]
            pid = f"i{i}_chorus"
            h.append(f'<tr><td class="sys">Chorus (ours)<small>one channel per speaker</small></td><td class="pl">{self.player(pid, c["mix"], c["ch"])}'
                     f'<button class="evbtn" data-audio="{pid}" data-t="{max(0.0, ev[0]-3.0):.2f}">Play from 3 s before the event</button></td>'
                     f'<td>{self.strip(pid, self.dur_of(c), self.rows_from_spans(c["spans"]), highlight=ev)}</td></tr>')
            g = it["gt"]
            pid = f"i{i}_gt"
            h.append(f'<tr><td class="sys">Ground truth<small>same transcript and speakers</small></td><td class="pl">{self.player(pid, g["mix"], g["ch"])}</td>'
                     f'<td>{self.strip(pid, self.dur_of(g), self.rows_from_spans(g["spans"]))}</td></tr>')
            h.append('</table></div>')
        return "".join(h)

    def sec_control(self):
        C = self.man["sections"]["control_cc2"]
        Sd = self.man["sections"]["control_sssd"]
        h = ['<h2 id="control">3. Timestamp mode</h2>']
        h.append('<p class="lead">Chorus has two modes for turn timing. In <b>turn-order mode</b>, the text input carries only the turn order and the model decides the timing. In <b>timestamp mode</b>, the text input also gives the start and end of every turn. The given turn timestamps are drawn in outline, so the activity strip shows how closely the generated speech follows them. Both rows come from the same model. This is the setting of Table 7 in the paper.</p>')
        h.append(self.legend())
        h.append('<h3>3a. Scripted conversations (CoVoMix2 test set). The turn timestamps place the turns in order with a fixed 0.4 s gap.</h3>')
        for i, it in enumerate(C["items"]):
            h.append(f'<div class="card"><h3>Conversation {i+1}</h3>')
            h.append(self.transcript(it["text"]))
            h.append('<table class="grid">')
            for key, name, sub in (("mode_o", "Turn-order mode", "turn order only"), ("mode_t", "Timestamp mode", "turn timestamps given")):
                e = it[key]
                pid = f"c{i}_{key}"
                rows = self.rows_from_layout(it["layout"]) + self.rows_from_spans(e["spans"])
                h.append(f'<tr><td class="sys">{name}<small>{sub}</small></td><td class="pl">{self.player(pid, e["mix"], e["ch"])}</td>'
                         f'<td>{self.strip(pid, max(self.dur_of(e), it["layout"][-1]["end"]+0.3), rows)}</td></tr>')
            h.append('</table></div>')
        h.append('<h3>3b. Spontaneous conversations (SSSD test set). The turn timestamps are those of the original recording.</h3>')
        if not self.sssd_recordings:
            h.append('<p class="sub">The prompt recordings are LibriTTS speakers, so the original recordings are not comparable and are not shown. Only their turn timestamps are given.</p>')
        for i, it in enumerate(Sd["items"]):
            h.append(f'<div class="card"><h3>Conversation {i+1}</h3>')
            h.append(self.transcript(it["text"]))
            h.append('<table class="grid">')
            if self.sssd_recordings and "gt" in it:
                e = it["gt"]
                pid = f"s{i}_gt"
                rows = self.rows_from_layout(it["layout"]) + self.rows_from_spans(e["spans"])
                h.append(f'<tr><td class="sys">Recording<small>defines the target</small></td><td class="pl">{self.player(pid, e["mix"], e["ch"])}</td>'
                         f'<td>{self.strip(pid, it["duration_gt"], rows)}</td></tr>')
            for key, name, sub in (("mode_o", "Turn-order mode", "turn order only"), ("mode_t", "Timestamp mode", "turn timestamps given")):
                e = it[key]
                pid = f"s{i}_{key}"
                rows = self.rows_from_layout(it["layout"]) + self.rows_from_spans(e["spans"])
                h.append(f'<tr><td class="sys">{name}<small>{sub}</small></td><td class="pl">{self.player(pid, e["mix"], e["ch"])}</td>'
                         f'<td>{self.strip(pid, max(self.dur_of(e), it["duration_gt"]), rows)}</td></tr>')
            h.append('</table></div>')
        return "".join(h)

    def sec_editing(self):
        S = self.man["sections"]["editing"]
        h = ['<h2 id="editing">4. Response generation</h2>']
        h.append('<p class="lead">One channel of a ground-truth conversation is given as its recording, and Chorus generates the channel of the other speaker from the transcript in turn-order mode. No timing is given, so the model decides when to start, when to backchannel and when to overlap. Both directions are shown, together with all-speaker generation of the same conversation. This is the setting of Table 8 in the paper.</p>')
        h.append(self.legend())
        for i, it in enumerate(S["items"]):
            h.append(f'<div class="card"><h3>Conversation {i+1}</h3>')
            h.append(self.transcript(it["text"]))
            h.append('<table class="grid">')
            g = it["gt"]
            pid = f"e{i}_gt"
            h.append(f'<tr><td class="sys">Ground truth<small>both channels given</small></td><td class="pl">{self.player(pid, g["mix"], g["ch"])}</td>'
                     f'<td>{self.strip(pid, self.dur_of(g), self.rows_from_spans(g["spans"]))}</td></tr>')
            for key in ("edit_ctx0", "edit_ctx1"):
                e = it["directions"][key]
                f, gch = e["fixed"], e["generated"]
                pid = f"e{i}_{key}"
                rows = []
                for k in range(2):
                    st = "hatch" if k == f else "fill"
                    rows.append({"label": f"Spk {CH_NAMES[k]}", "spans": e["spans"][k], "color": CH_COLORS[k], "style": st})
                labels = [f"Speaker {CH_NAMES[k]} ({'given' if k == f else 'generated'})" for k in range(2)]
                h.append(f'<tr><td class="sys">Speaker {CH_NAMES[f]} given, speaker {CH_NAMES[gch]} generated<small>response generation</small></td>'
                         f'<td class="pl">{self.player(pid, e["mix"], e["ch"], labels)}</td>'
                         f'<td>{self.strip(pid, self.dur_of(e), rows)}</td></tr>')
            b = it["both"]
            pid = f"e{i}_both"
            h.append(f'<tr><td class="sys">All-speaker generation<small>both channels generated</small></td><td class="pl">{self.player(pid, b["mix"], b["ch"])}</td>'
                     f'<td>{self.strip(pid, self.dur_of(b), self.rows_from_spans(b["spans"]))}</td></tr>')
            h.append('</table></div>')
        return "".join(h)

    def sec_ami(self):
        S = self.man["sections"]["ami"]
        h = ['<h2 id="multi">5. More than two speakers (AMI test set)</h2>']
        h.append('<p class="lead">The same model runs with two, three or four copies, one channel per speaker. The transcripts and turn order come from the AMI test set. The prompt recordings are LibriTTS speakers, so the original meeting audio is not comparable and is not shown. This is the setting of Table 5 in the paper.</p>')
        h.append(self.legend())
        byK = {}
        for it in S["items"]:
            byK.setdefault(it["K"], []).append(it)
        for K in sorted(byK):
            h.append(f'<div class="kgroup"><h3>n = {K} speakers</h3>')
            for i, it in enumerate(byK[K]):
                h.append(f'<div class="card"><h3>Conversation {i+1}</h3>')
                h.append(self.transcript(it["text"]))
                h.append('<table class="grid">')
                c = it["chorus"]
                pid = f"a{K}_{i}_chorus"
                h.append(f'<tr><td class="sys">Chorus (ours)<small>one channel per speaker</small></td><td class="pl">{self.player(pid, c["mix"], c["ch"])}</td>'
                         f'<td>{self.strip(pid, self.dur_of(c), self.rows_from_spans(c["spans"]))}</td></tr>')
                h.append('</table></div>')
            h.append('</div>')
        return "".join(h)

    def header(self):
        return f"""
<h1>{esc(TITLE)}</h1>
<p class="sub">Audio samples. Anonymous supplementary material. These samples are for ICLR submission only.</p>
<p class="lead">Chorus duplicates a pretrained single-speaker TTS model, one copy per speaker, and lets the copies communicate through Transform-Average-Concatenate (TAC) blocks. Each copy generates one audio channel for its speaker. The average step of TAC is invariant to the number of speakers, so the number of speakers is chosen at inference.</p>
<img class="fig" src="assets/architecture.png" alt="(a) Chorus with two weight-shared single-speaker TTS models, one channel per speaker, joined by a TAC block after every DiT block; (b) the TAC block: transform, average over speakers, concatenate, gated residual">
<div class="note"><b>Listening notes.</b> Chorus generates one channel per speaker. <b>Mix</b> is the sum of the channels, the single-channel mixture that the paper evaluates. The speaker buttons play one channel alone. The activity strips show where each channel contains speech, computed with the voice activity detection (VAD) of pyannote. Audio is 24 kHz WAV. Headphones recommended.</div>
<p class="sub">Contents: <a href="#two-speaker">1. Two-speaker conversation</a> · <a href="#interaction">2. Speaker interaction</a> · <a href="#control">3. Timestamp mode</a> · <a href="#editing">4. Response generation</a> · <a href="#multi">5. More than two speakers</a></p>
"""

    def footer(self):
        return """
<footer>
<p>These samples are for ICLR submission only.</p>
</footer>
"""

    def build(self):
        body = [self.header(), self.sec_grid(), self.sec_interaction(), self.sec_control(), self.sec_editing(), self.sec_ami(), self.footer()]
        page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chorus: audio samples</title>
<style>{CSS}</style>
</head>
<body>
<main>
{''.join(body)}
</main>
<script>{JS}</script>
</body>
</html>
"""
        (self.out / "index.html").write_text(page)
        return len(self.copied)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--out", default=str(HERE))
    ap.add_argument("--sssd-recordings", action="store_true", help="include the original SSSD recordings in section 3b")
    a = ap.parse_args()
    b = Builder(Path(a.bundle), Path(a.out), a.sssd_recordings)
    n = b.build()
    total = sum(p.stat().st_size for p in (Path(a.out) / "audio").rglob("*.wav"))
    print(f"wrote index.html with {b.n_audio} players, {n} audio files, {total/1e6:.1f} MB")


if __name__ == "__main__":
    main()
