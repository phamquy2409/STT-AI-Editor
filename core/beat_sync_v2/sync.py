
from __future__ import annotations
import csv, json, os, math
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
DEFAULT_SOURCE_FOLDER = "D:/5thang5test"

def appdata_dir() -> Path:
    p = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "STT_AI_Editor"
    p.mkdir(parents=True, exist_ok=True)
    return p

def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}

def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def write_csv(path: Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in rows: w.writerow({c:r.get(c,"") for c in cols})

def outdir(project_root: Path, name: str) -> Path:
    p = project_root / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p

def open_path(path: Path) -> None:
    try: os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception: pass

def fnum(v: Any, default: float=0.0) -> float:
    try:
        if v is None or v=="": return default
        return float(v)
    except Exception: return default

def inum(v: Any, default: int=0) -> int:
    try:
        if v is None or v=="": return default
        return int(float(v))
    except Exception: return default

def sec_to_frames(sec: float, timebase: int=25) -> int:
    return int(round(max(0.0, sec)*timebase))

def frames_to_sec(frames: int, timebase: int=25) -> float:
    return max(0.0, frames/max(1,timebase))

def norm_event(event: str) -> str:
    event=str(event or 'general')
    return {'family':'gia_tien','ceremony':'gia_tien','traditional':'gia_tien','speech':'vow_speech','vow':'vow_speech','party':'dance_party','dance':'dance_party'}.get(event,event)

def section_for_time(t: float, target_seconds: float) -> str:
    pos=t/max(1.0,target_seconds)
    if pos<0.12: return 'intro'
    if pos<0.42: return 'story'
    if pos<0.58: return 'build'
    if pos<0.82: return 'climax'
    return 'ending'

def load_analyzer_items(project_root: Path) -> list[dict[str,Any]]:
    d=read_json(project_root/'stt_wedding_source_analyzer_v2.json') or read_json(appdata_dir()/'stt_wedding_source_analyzer_v2.json')
    out=[]
    for item in list(d.get('items') or []):
        if str(item.get('file') or ''):
            x=dict(item); x['event']=norm_event(str(x.get('event') or 'general')); out.append(x)
    return out

def load_cut_points(project_root: Path) -> dict[str,Any]:
    d=read_json(project_root/'stt_real_audio_beat_energy_v1.json') or read_json(appdata_dir()/'stt_real_audio_beat_energy_v1.json')
    pts=[]
    dur=fnum(d.get('analyze_seconds'),180)
    for p in list(d.get('cut_points') or []):
        t=fnum(p.get('time_sec'),-1)
        if t>=0:
            q=dict(p); q['time_sec']=t; q['section']=str(q.get('section') or section_for_time(t,dur)); pts.append(q)
    pts.sort(key=lambda x:fnum(x.get('time_sec'),0))
    d['cut_points']=pts
    return d

def item_rank(item: dict[str,Any]) -> float:
    score=fnum(item.get('score'),0)
    decision=str(item.get('decision') or '').lower()
    flags=str(item.get('quality_flags') or '')
    reason=str(item.get('reason') or '')
    motion=fnum(item.get('motion_score'),0); blur=fnum(item.get('blur_score'),0); bright=fnum(item.get('brightness'),0)
    if decision=='strong_pick': score+=25
    elif decision=='keep': score+=14
    elif decision=='review': score-=1
    elif decision=='reject': score-=100
    if 'possible_out_focus' in flags: score-=28
    if 'too_dark' in flags or 'too_bright' in flags: score-=22
    if 'low_contrast' in flags: score-=8
    if 'heavy_motion_possible_shake' in reason: score-=18
    if blur>=120: score+=8
    elif 0<blur<35: score-=16
    if 45<=bright<=210: score+=5
    elif bright>0: score-=5
    if 4<=motion<=35: score+=5
    elif motion>55: score-=18
    if fnum(item.get('duration_sec'),0)<1.2: score-=80
    return round(score,3)

def hard_skip(item: dict[str,Any]) -> bool:
    decision=str(item.get('decision') or '').lower(); flags=str(item.get('quality_flags') or '')
    if decision=='reject': return True
    if 'cannot_open' in flags or 'too_few_frames' in flags: return True
    if fnum(item.get('duration_sec'),0)<1.2: return True
    return False

def section_events(section: str) -> list[str]:
    return {
        'intro':['details','getting_ready','gia_tien','reception'],
        'story':['getting_ready','details','gia_tien','ruoc_dau','reception'],
        'build':['gia_tien','ruoc_dau','reception','vow_speech'],
        'climax':['vow_speech','reception','dance_party','gia_tien','ruoc_dau'],
        'ending':['vow_speech','dance_party','reception','details'],
    }.get(section,['general'])

def target_shots_by_section(target_shots:int)->dict[str,int]:
    weights={'intro':0.14,'story':0.27,'build':0.16,'climax':0.30,'ending':0.13}
    counts={k:max(2,int(round(target_shots*v))) for k,v in weights.items()}
    diff=target_shots-sum(counts.values()); order=['climax','story','build','intro','ending']; i=0
    while diff!=0:
        k=order[i%len(order)]
        if diff>0: counts[k]+=1; diff-=1
        elif counts[k]>2: counts[k]-=1; diff+=1
        i+=1
    return counts

def section_bounds(target_seconds:float)->dict[str,tuple[float,float]]:
    return {'intro':(0,target_seconds*.12),'story':(target_seconds*.12,target_seconds*.42),'build':(target_seconds*.42,target_seconds*.58),'climax':(target_seconds*.58,target_seconds*.82),'ending':(target_seconds*.82,target_seconds)}

def nearest_peak(points:list[dict[str,Any]], ideal:float, lo:float, hi:float, section:str)->tuple[float,str,float]:
    cand=[]
    for p in points:
        t=fnum(p.get('time_sec'),0)
        if lo<=t<=hi:
            energy=fnum(p.get('energy'),0.3); sec=str(p.get('section') or '')
            score=abs(t-ideal)-energy*.35
            if sec==section: score-=.25
            cand.append((score,t,str(p.get('source') or 'peak'),energy))
    if not cand: return round(ideal,3),'ideal_grid_no_peak',0.0
    cand.sort(key=lambda x:x[0]); return round(cand[0][1],3),cand[0][2],round(cand[0][3],4)

def build_boundaries(points:list[dict[str,Any]], target_seconds:float, target_shots:int)->list[dict[str,Any]]:
    counts=target_shots_by_section(target_shots); bounds=section_bounds(target_seconds)
    boundaries=[{'time_sec':0.0,'section':'intro','source':'start','energy':0.0}]
    for section in ['intro','story','build','climax','ending']:
        s,e=bounds[section]; count=counts[section]
        for i in range(1,count+1):
            ideal=s+(e-s)*i/count
            if ideal>=target_seconds: continue
            window=.55 if section in {'intro','climax'} else .9
            lo=max(s,ideal-window); hi=min(e,ideal+window)
            t,src,energy=nearest_peak(points,ideal,lo,hi,section)
            if t-boundaries[-1]['time_sec']<.55: t=boundaries[-1]['time_sec']+.55
            if t<target_seconds: boundaries.append({'time_sec':round(t,3),'section':section,'source':src,'energy':energy})
    if boundaries[-1]['time_sec']<target_seconds:
        boundaries.append({'time_sec':round(target_seconds,3),'section':'ending','source':'end','energy':0.0})
    clean=[boundaries[0]]
    for b in boundaries[1:]:
        if b['time_sec']-clean[-1]['time_sec']>=.5: clean.append(b)
    if clean[-1]['time_sec']<target_seconds:
        clean.append({'time_sec':round(target_seconds,3),'section':'ending','source':'end','energy':0.0})
    return clean

def pick_items(items:list[dict[str,Any]], spans:list[dict[str,Any]])->list[dict[str,Any]]:
    buckets={}
    for item in items:
        if hard_skip(item): continue
        x=dict(item); x['rank_score']=item_rank(x); buckets.setdefault(str(x.get('event') or 'general'),[]).append(x)
    for k in buckets: buckets[k].sort(key=lambda x:(-fnum(x.get('rank_score'),0),inum(x.get('source_order'),999999)))
    used=set(); picked=[]
    pool=sorted([x for b in buckets.values() for x in b], key=lambda x:(-fnum(x.get('rank_score'),0),inum(x.get('source_order'),999999)))
    for span in spans:
        section=str(span.get('section') or 'story'); chosen=None
        for event in section_events(section):
            for item in buckets.get(event,[]):
                f=str(item.get('file') or '')
                if f and f not in used: chosen=item; break
            if chosen: break
        if chosen is None:
            for item in pool:
                f=str(item.get('file') or '')
                if f and f not in used: chosen=item; break
        if chosen is None: break
        used.add(str(chosen.get('file') or '')); picked.append(chosen)
    return picked

def create_beat_sync_v2_more_cut_points(project_root: str|Path=DEFAULT_PROJECT_ROOT, source_folder: str|Path=DEFAULT_SOURCE_FOLDER, target_seconds:float=180.0, target_shots:int=76, timebase:int=25, open_folder:bool=True, **kwargs:Any)->dict[str,Any]:
    project_root=Path(project_root); out=outdir(project_root,'beat_sync_v2_more_cut_points')
    beat_data=load_cut_points(project_root); points=list(beat_data.get('cut_points') or [])
    items=load_analyzer_items(project_root)
    if len(points)<3:
        res={'ok':False,'error':'NO_CUT_POINTS','message':'Run 118 first.'}; write_json(out/'beat_sync_v2_error.json',res); open_path(out) if open_folder else None; return res
    if not items:
        res={'ok':False,'error':'NO_ANALYZER_ITEMS','message':'Run 110 first.'}; write_json(out/'beat_sync_v2_error.json',res); open_path(out) if open_folder else None; return res
    boundaries=build_boundaries(points,target_seconds,target_shots)
    spans=[]
    for i in range(len(boundaries)-1):
        s=fnum(boundaries[i].get('time_sec'),0); e=fnum(boundaries[i+1].get('time_sec'),s)
        if e>s:
            spans.append({'index':len(spans)+1,'start_sec':round(s,3),'end_sec':round(e,3),'duration_sec':round(e-s,3),'section':str(boundaries[i].get('section') or section_for_time(s,target_seconds)),'cut_source':str(boundaries[i+1].get('source') or ''),'cut_energy':fnum(boundaries[i+1].get('energy'),0)})
    picked=pick_items(items,spans); n=min(len(spans),len(picked)); spans=spans[:n]; picked=picked[:n]
    timeline=[]
    ratios=[.12,.18,.25,.33,.42,.52,.62]
    for idx,(span,item) in enumerate(zip(spans,picked),start=1):
        dur=fnum(span.get('duration_sec'),1.0); src_dur=max(1.0,fnum(item.get('duration_sec'),10.0))
        if src_dur<=dur+.3: src_in_sec=0.0
        else: src_in_sec=max(0.0,min(src_dur-dur-.1,src_dur*ratios[idx%len(ratios)]))
        src_out_sec=min(src_dur,src_in_sec+dur); real_dur=max(.1,src_out_sec-src_in_sec)
        start_sec=fnum(span.get('start_sec'),0); end_sec=start_sec+real_dur
        timeline.append({'index':idx,'file':str(item.get('file') or ''),'filename':str(item.get('filename') or Path(str(item.get('file') or '')).name),'event':str(item.get('event') or 'general'),'role':str(item.get('event') or 'general'),'section':str(span.get('section') or 'story'),'energy':'beat_sync_v2','decision':str(item.get('decision') or ''),'score':fnum(item.get('score'),0),'rank_score':fnum(item.get('rank_score'),0),'quality_flags':str(item.get('quality_flags') or ''),'timeline_start':sec_to_frames(start_sec,timebase),'timeline_end':sec_to_frames(end_sec,timebase),'source_in':sec_to_frames(src_in_sec,timebase),'source_out':sec_to_frames(src_out_sec,timebase),'duration':round(real_dur,3),'duration_sec':round(real_dur,3),'source_duration_sec':src_dur,'source_order':inum(item.get('source_order'),0),'beat_locked':True,'beat_v2':True,'beat_target_start_sec':round(start_sec,3),'beat_target_end_sec':round(fnum(span.get('end_sec'),end_sec),3),'beat_cut_source':str(span.get('cut_source') or ''),'beat_cut_energy':fnum(span.get('cut_energy'),0),'beat_offset_ms':0,'reason':f"121_BEAT_SYNC_V2 section={span.get('section')} cut={span.get('cut_source')} energy={span.get('cut_energy')}"})
    sequence_seconds=max([frames_to_sec(inum(x.get('timeline_end'),0),timebase) for x in timeline]+[0])
    section_counts={}; event_counts={}
    for item in timeline:
        section_counts[str(item['section'])]=section_counts.get(str(item['section']),0)+1
        event_counts[str(item['event'])]=event_counts.get(str(item['event']),0)+1
    data={'ok':True,'module':'121_beat_sync_v2_more_cut_points','updated_at':datetime.now().isoformat(timespec='seconds'),'target_seconds':target_seconds,'target_shots':target_shots,'timeline_count':len(timeline),'timeline_seconds':round(sequence_seconds,3),'cut_point_count':len(points),'boundary_count':len(boundaries),'used_real_audio':bool(beat_data.get('used_real_audio')),'section_counts':section_counts,'event_counts':event_counts,'timeline':timeline}
    for name in ['stt_beat_sync_v2_timeline_v1.json','stt_beat_locked_timeline_v1.json','stt_music_synced_timeline_v1.json','stt_smart_wedding_timeline_v1.json','stt_prewedding_refined_v1.json']:
        write_json(project_root/name,data)
    write_json(appdata_dir()/'stt_prewedding_refined_v1.json',data)
    write_json(out/'stt_beat_sync_v2_timeline_v1.json',data)
    write_csv(out/'BEAT_SYNC_V2_TIMELINE.csv',timeline,['index','filename','event','section','timeline_start','timeline_end','source_in','source_out','duration','beat_cut_source','beat_cut_energy','decision','rank_score','file'])
    (out/'BEAT_SYNC_V2_REPORT.html').write_text(html_table('Beat Sync V2 / More Cut Points',timeline,['index','filename','event','section','duration','beat_cut_source','beat_cut_energy'],'121 tăng số shot, intro/climax cắt nhanh hơn, rải clip sát real cut point hơn.'),encoding='utf-8')
    if open_folder: open_path(out)
    return {'ok':True,'report_dir':str(out),'timeline_count':len(timeline),'timeline_seconds':round(sequence_seconds,3),'cut_point_count':len(points),'used_real_audio':bool(beat_data.get('used_real_audio')),'section_counts':section_counts,'fix':'121_beat_sync_v2_more_cut_points'}

def html_table(title:str, rows:list[dict[str,Any]], cols:list[str], note:str='')->str:
    import html
    th=''.join(f'<th>{html.escape(str(c))}</th>' for c in cols)
    tr=''.join('<tr>'+''.join(f'<td>{html.escape(str(r.get(c,"")))}</td>' for c in cols)+'</tr>' for r in rows)
    return "<!doctype html><html><head><meta charset='utf-8'><style>body{font-family:Arial;background:#111;color:#eee;margin:32px}.card{background:#181818;border:1px solid #333;border-radius:16px;padding:24px}td,th{border-bottom:1px solid #333;padding:8px;text-align:left;font-size:13px}</style></head>"+f"<body><div class='card'><h1>{html.escape(title)}</h1><p>{html.escape(note)}</p><table><tr>{th}</tr>{tr}</table></div></body></html>"
